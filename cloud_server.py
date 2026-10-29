import json
import os
import re

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from pypdf import PdfReader


SOURCE = "https://www.antiguamet.com/Daily_FCast.html"
MARINE_STATUS = "https://www.antiguamet.com/Marine.html"

MARINE_BULLETINS = {
    "High Surf Advisory":
        "https://www.antiguamet.com/Antigua_Met_files/HighSurfADVISORY.pdf",

    "High Surf Warning":
        "https://www.antiguamet.com/Antigua_Met_files/HighSurfWARNING.pdf",

    "Small Craft Advisory":
        "https://www.antiguamet.com/Antigua_Met_files/SmallCraftADVISORY.pdf",

    "Small Craft Warning":
        "https://www.antiguamet.com/Antigua_Met_files/SmallCraftWARNING.pdf",
}

ANTIGUA_TIME = ZoneInfo("America/Antigua")

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def fetch(url):
    request = Request(
        url,
        headers={
            "User-Agent": "SeaPoint/0.1",
        },
    )

    with urlopen(request, timeout=20) as response:
        return response.read()


def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def pdf_to_text(data):
    reader = PdfReader(
        BytesIO(data)
    )

    text = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text.append(page_text)

    return "\n".join(text)


def get_current_marine_links():
    page = fetch(
        MARINE_STATUS
    ).decode(
        "utf-8",
        errors="ignore",
    )

    anchors = re.findall(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        page,
        re.IGNORECASE | re.DOTALL,
    )

    found = {}

    for href, label_html in anchors:
        label = re.sub(
            r"<[^>]+>",
            " ",
            label_html,
        )

        label = normalize_text(
            unescape(label)
        )

        for name in MARINE_BULLETINS:
            if name.lower() in label.lower():
                found[name] = urljoin(
                    MARINE_STATUS,
                    href,
                )

    if not found:
        found = dict(
            MARINE_BULLETINS
        )

    return found


def parse_issue_datetime(text):
    pattern = re.compile(
        r"(\d{1,2}:\d{2}\s*(?:am|pm))\s+"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
        r"(\d{1,2})\s+"
        r"([A-Za-z]+),?\s+"
        r"(\d{4})",
        re.IGNORECASE,
    )

    match = pattern.search(text)

    if not match:
        return None, None

    value = (
        f"{match.group(1).upper()} "
        f"{match.group(2)} "
        f"{match.group(3)} "
        f"{match.group(4)}"
    )

    for date_format in (
        "%I:%M %p %d %B %Y",
        "%I:%M %p %d %b %Y",
    ):
        try:
            result = datetime.strptime(
                value,
                date_format,
            )

            return (
                result.replace(
                    tzinfo=ANTIGUA_TIME,
                ),
                match,
            )

        except ValueError:
            pass

    return None, None


def bulletin_applies_to_antigua(
    text,
    issue_match,
):
    if issue_match is None:
        return False

    after_issue = text[
        issue_match.end():
    ]

    end_match = re.search(
        r"Locations\s+to\s+be\s+affected:|Timing:",
        after_issue,
        re.IGNORECASE,
    )

    if end_match:
        after_issue = after_issue[
            :end_match.start()
        ]

    return re.search(
        r"\bAntigua\b",
        after_issue,
        re.IGNORECASE,
    ) is not None


def parse_descriptor(
    descriptor,
    issue_datetime,
):
    descriptor = normalize_text(
        descriptor
    )

    lower = descriptor.lower()

    target_date = None

    full_date = re.search(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        descriptor,
        re.IGNORECASE,
    )

    if full_date:
        day = full_date.group(1)
        month = full_date.group(2)
        year = full_date.group(3)

        for date_format in (
            "%d %B %Y",
            "%d %b %Y",
        ):
            try:
                target_date = datetime.strptime(
                    f"{day} {month} {year}",
                    date_format,
                ).date()

                break

            except ValueError:
                pass

    if target_date is None:
        weekday_match = re.search(
            r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            descriptor,
            re.IGNORECASE,
        )

        if weekday_match:
            weekday = WEEKDAYS[
                weekday_match.group(1).lower()
            ]

            days_ahead = (
                weekday -
                issue_datetime.weekday()
            ) % 7

            target_date = (
                issue_datetime.date()
                + timedelta(
                    days=days_ahead,
                )
            )

    if target_date is None:
        if "tomorrow" in lower:
            target_date = (
                issue_datetime.date()
                + timedelta(days=1)
            )

        elif (
            "today" in lower
            or "tonight" in lower
            or "this evening" in lower
            or "this afternoon" in lower
        ):
            target_date = (
                issue_datetime.date()
            )

        else:
            return None

    explicit_time = re.search(
        r"\b(\d{1,2})"
        r"(?::(\d{2}))?\s*"
        r"(am|pm)\b",
        descriptor,
        re.IGNORECASE,
    )

    if explicit_time:
        hour = int(
            explicit_time.group(1)
        )

        minute = int(
            explicit_time.group(2) or 0
        )

        meridiem = (
            explicit_time.group(3).lower()
        )

        if (
            meridiem == "pm"
            and hour != 12
        ):
            hour += 12

        elif (
            meridiem == "am"
            and hour == 12
        ):
            hour = 0

        target_time = time(
            hour,
            minute,
        )

    elif "mid-morning" in lower:
        target_time = time(10, 0)

    elif "dawn" in lower:
        target_time = time(6, 0)

    elif (
        "morning" in lower
        or "noon" in lower
    ):
        target_time = time(12, 0)

    elif "afternoon" in lower:
        target_time = time(18, 0)

    elif "evening" in lower:
        target_time = time(21, 0)

    else:
        target_time = time(23, 59)

    return datetime.combine(
        target_date,
        target_time,
        tzinfo=ANTIGUA_TIME,
    )


def get_timing_window(
    text,
    issue_datetime,
    applies_to_antigua,
):
    timing_match = re.search(
        r"Timing:\s*(.*?)(?=Synopsis:)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not timing_match:
        return None, None

    timing_text = normalize_text(
        timing_match.group(1)
    )

    lower = timing_text.lower()

    antigua_index = lower.find(
        "antigua"
    )

    if antigua_index >= 0:
        until_index = lower.rfind(
            "until",
            0,
            antigua_index,
        )

        if until_index < 0:
            return None, None

        descriptor_end = (
            antigua_index
        )

        for_index = lower.find(
            " for ",
            until_index,
            antigua_index,
        )

        if for_index >= 0:
            descriptor_end = (
                for_index
            )

        expiry_descriptor = (
            timing_text[
                until_index
                + len("until"):
                descriptor_end
            ]
        )

        from_index = lower.rfind(
            "from",
            0,
            until_index,
        )

        start_descriptor = None

        if from_index >= 0:
            between = lower[
                from_index:
                until_index
            ]

            if " for " not in between:
                start_descriptor = (
                    timing_text[
                        from_index
                        + len("from"):
                        until_index
                    ]
                )

    else:
        if not applies_to_antigua:
            return None, None

        if " for " in lower:
            return None, None

        until_match = re.search(
            r"\buntil\s+(.+?)(?:[.;]|$)",
            timing_text,
            re.IGNORECASE,
        )

        if not until_match:
            return None, None

        expiry_descriptor = (
            until_match.group(1)
        )

        from_match = re.search(
            r"\bfrom\s+(.+?)\s+until\b",
            timing_text,
            re.IGNORECASE,
        )

        start_descriptor = (
            from_match.group(1)
            if from_match
            else None
        )

    expiry = parse_descriptor(
        expiry_descriptor,
        issue_datetime,
    )

    if start_descriptor:
        start = parse_descriptor(
            start_descriptor,
            issue_datetime,
        )
    else:
        start = issue_datetime

    return start, expiry


def check_alert(item):
    name, url = item

    try:
        pdf_data = fetch(url)

        text = normalize_text(
            pdf_to_text(pdf_data)
        )

        issue_datetime, issue_match = (
            parse_issue_datetime(text)
        )

        if issue_datetime is None:
            return name, {
                "active": False,
                "reason":
                    "issue_date_unreadable",
            }

        applies = (
            bulletin_applies_to_antigua(
                text,
                issue_match,
            )
        )

        if not applies:
            return name, {
                "active": False,
                "reason":
                    "not_for_antigua",
            }

        start, expiry = (
            get_timing_window(
                text,
                issue_datetime,
                applies,
            )
        )

        if (
            start is None
            or expiry is None
        ):
            return name, {
                "active": False,
                "reason":
                    "timing_unreadable",
            }

        now = datetime.now(
            ANTIGUA_TIME
        )

        if start > expiry:
            return name, {
                "active": False,
                "reason":
                    "invalid_timing",
            }

        if now < start:
            return name, {
                "active": False,
                "reason":
                    "not_started",
                "starts":
                    start.isoformat(),
                "expires":
                    expiry.isoformat(),
            }

        if now > expiry:
            return name, {
                "active": False,
                "reason":
                    "expired",
                "expires":
                    expiry.isoformat(),
            }

        return name, {
            "active": True,
            "reason": "active",
            "starts":
                start.isoformat(),
            "expires":
                expiry.isoformat(),
            "url": url,
        }

    except Exception as error:
        return name, {
            "active": False,
            "reason":
                "bulletin_error",
            "error":
                str(error),
        }


class Handler(
    BaseHTTPRequestHandler
):

    def send_cors_headers(self):
        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

    def send_json(
        self,
        data,
        status=200,
    ):
        content = json.dumps(
            data,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_cors_headers()

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)

        self.send_cors_headers()

        self.end_headers()

    def do_GET(self):

        if self.path == "/health":
            self.send_json({
                "status": "ok",
                "service":
                    "SeaPoint Alerts",
            })

            return

        if self.path == "/alerts":
            try:
                current_links = (
                    get_current_marine_links()
                )

                active_alerts = []
                checked = {}

                with ThreadPoolExecutor(
                    max_workers=4,
                ) as executor:

                    results = executor.map(
                        check_alert,
                        current_links.items(),
                    )

                    for (
                        name,
                        result,
                    ) in results:

                        checked[name] = (
                            result
                        )

                        if result["active"]:
                            active_alerts.append(
                                name
                            )

                self.send_json({
                    "alerts":
                        active_alerts,
                    "checked":
                        checked,
                })

            except Exception as error:
                self.send_json(
                    {
                        "alerts": [],
                        "error":
                            str(error),
                    },
                    502,
                )

            return

        if self.path.startswith(
            "/marine-alert/"
        ):
            alert_name = unquote(
                self.path.removeprefix(
                    "/marine-alert/"
                )
            )

            url = (
                MARINE_BULLETINS.get(
                    alert_name
                )
            )

            if url is None:
                self.send_error(404)

                return

            try:
                content = fetch(url)

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/pdf",
                )

                self.send_cors_headers()

                self.end_headers()

                self.wfile.write(
                    content
                )

            except Exception as error:
                self.send_json(
                    {
                        "error":
                            str(error),
                    },
                    502,
                )

            return

        if self.path == "/bulletin":
            try:
                content = fetch(
                    SOURCE
                )

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )

                self.send_cors_headers()

                self.end_headers()

                self.wfile.write(
                    content
                )

            except Exception as error:
                self.send_json(
                    {
                        "error":
                            str(error),
                    },
                    502,
                )

            return

        self.send_error(404)


PORT = int(
    os.environ.get(
        "PORT",
        "8000",
    )
)

print(
    f"SeaPoint backend running on port {PORT}"
)

ThreadingHTTPServer(
    (
        "0.0.0.0",
        PORT,
    ),
    Handler,
).serve_forever()