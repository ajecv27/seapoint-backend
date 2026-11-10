"""Current, local Antigua/Barbuda alerts from verified official products.

A missing, stale or unreadable bulletin is unknown coverage, not an all-clear.
The injected marine loader keeps the existing PDF parser independent of the
HTML statement readers. No third-party packages are required.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import re
import threading
from urllib.request import Request, urlopen

LOCAL_TIME = timezone(timedelta(hours=-4))
MARINE_PRODUCTS = {
    "High Surf Advisory": "https://www.antiguamet.com/Antigua_Met_files/HighSurfADVISORY.pdf",
    "High Surf Warning": "https://www.antiguamet.com/Antigua_Met_files/HighSurfWARNING.pdf",
    "Small Craft Advisory": "https://www.antiguamet.com/Antigua_Met_files/SmallCraftADVISORY.pdf",
    "Small Craft Warning": "https://www.antiguamet.com/Antigua_Met_files/SmallCraftWARNING.pdf",
}
SOURCES = {
    "tropical:watch": "https://www.antiguamet.com/WATCH_STATEMENTS/watchStatement_Antigua%20and%20Barbuda.html",
    "tropical:warning": "https://www.antiguamet.com/WARNING_STATEMENTS/warningStatement_Antigua%20and%20Barbuda.html",
    "flood:advisory": "https://www.antiguamet.com/ADVISORY_STATEMENTS/advisoryStatement.html",
    "flood:statement": "https://www.antiguamet.com/FLOOD_STATEMENTS/floodStatement.html",
    "flood:watch": "https://www.antiguamet.com/FLOODWATCH_STATEMENTS/floodwatchStatement.html",
    "flood:warning": "https://www.antiguamet.com/FLOODWARNING_STATEMENTS/floodWarningStatement.html",
}
_MONTH = r"(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:TEMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)"
_DATE = re.compile(rf"\b(?:(?P<month>{_MONTH})\s+(?P<day>\d{{1,2}})(?:ST|ND|RD|TH)?|(?P<day2>\d{{1,2}})(?:ST|ND|RD|TH)?\s+(?P<month2>{_MONTH}))[ ,]+(?P<year>20\d{{2}})\b", re.I)
_TIME = re.compile(r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>AM|PM|MIDDAY|NOON|MIDNIGHT)\b", re.I)
_PRODUCT = r"(?P<kind>TROPICAL\s+STORM|HURRICANE|FLASH\s*FLOOD|FLOOD)\s+(?P<level>WATCH|WARNING|ADVISORY)"
_OPERATIVE = re.compile(_PRODUCT + r"\s+(?:IS\s+(?:NOW\s+)?IN\s+EFFECT|REMAINS?\s+IN\s+EFFECT|CONTINUES?\s+IN\s+EFFECT|(?:HAS\s+BEEN|IS)\s+(?:ISSUED|EXTENDED))\s+(?:FOR|IN)\s+", re.I)
_NEXT_PRODUCT = re.compile(r"(?:TROPICAL\s+STORM|HURRICANE|FLASH\s*FLOOD|FLOOD)\s+(?:WATCH|WARNING|ADVISORY)\b", re.I)
_CANCEL = re.compile(r"\b(?:DISCONTINUED|CANCELLED|CANCELED|LIFTED)\b", re.I)
_AFFIRMATIVE_CANCEL = re.compile(r"\b(?:(?:HAS|HAVE)\s+(?:NOW\s+)?(?:BEEN\s+)?|(?:IS|ARE)\s+(?:NOW\s+)?)(?:DISCONTINUED|CANCELLED|CANCELED|LIFTED)\b", re.I)
_MONTHS = {name: i for i, name in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _text(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    parser = _Text()
    parser.feed(str(raw))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip().upper()


def _aware(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value):
    return _aware(value).isoformat()


def _from_iso(value):
    try:
        return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except (ValueError, TypeError, AttributeError):
        return None


def _date_parts(match):
    return (int(match["year"]), _MONTHS[(match["month"] or match["month2"])[:3].upper()], int(match["day"] or match["day2"]))


def _hour_parts(match):
    hour, minute = int(match["hour"]), int(match["minute"] or 0)
    if hour < 1 or hour > 12 or minute > 59:
        raise ValueError("invalid clock time")
    period = match["period"].upper()
    if period in ("MIDDAY", "NOON"):
        return 12, minute
    if period == "MIDNIGHT":
        return 0, minute
    return hour % 12 + (12 if period == "PM" else 0), minute


def _issue(text):
    # The issue timestamp is in the header. A validity/next-update timestamp
    # later in an unreadable bulletin must never be mistaken for its issue.
    boundaries = [match.start() for pattern in (_OPERATIVE, _CANCEL, re.compile(r"\b(?:UNTIL|EXPIRES?|THE NEXT\s+(?:ADVISORY|UPDATE|BULLETIN))\b")) if (match := pattern.search(text))]
    header = text[:min(boundaries)] if boundaries else text
    for date in _DATE.finditer(header):
        prefix = header[max(0, date.start() - 65):date.start()]
        times = list(_TIME.finditer(prefix))
        if not times:
            continue
        try:
            hour, minute = _hour_parts(times[-1])
            tz = timezone.utc if re.search(r"\b(?:UTC|GMT)\b", prefix[times[-1].end():]) else LOCAL_TIME
            return datetime(*_date_parts(date), hour, minute, tzinfo=tz)
        except ValueError:
            return None
    # ISO is accepted only when explicitly labelled as an issue timestamp.
    match = re.search(r"\bISSUED(?:\s+AT)?\s*:?\s*(20\d\d-\d\d-\d\dT\d\d:\d\d(?::\d\d)?(?:Z|[+-]\d\d:\d\d))", header, re.I)
    return _from_iso(match[1]) if match else None


def _relative_time(fragment, issued, next_update=False):
    iso = re.search(r"20\d\d-\d\d-\d\dT\d\d:\d\d(?::\d\d)?(?:Z|[+-]\d\d:\d\d)", fragment, re.I)
    if iso:
        return _from_iso(iso[0])
    clock = _TIME.search(fragment)
    if not clock:
        return None
    try:
        hour, minute = _hour_parts(clock)
        date = _DATE.search(fragment)
        base = issued.astimezone(LOCAL_TIME)
        if date:
            value = datetime(*_date_parts(date), hour, minute, tzinfo=LOCAL_TIME)
        else:
            value = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if "TOMORROW" in fragment:
                value += timedelta(days=1)
            elif next_update and value <= base:
                value += timedelta(days=1)
        return value
    except ValueError:
        return None


def _islands(scope):
    return [island.title() for island in ("ANTIGUA", "BARBUDA") if re.search(r"\b" + island + r"\b", scope)]


def parse_marine_locations(text, issue_end):
    """Return explicitly covered local islands from the marine region heading.

    ``issue_end`` is the end offset of the already-validated PDF issue match.
    An empty result means local coverage was not established; callers must keep
    ambiguous geography unknown. Issuer addresses and later forecast text do
    not establish bulletin coverage.
    """
    if not isinstance(issue_end, int) or not 0 <= issue_end <= len(text):
        return []
    header = text[issue_end:]
    header = re.split(r"Locations\s+to\s+be\s+affected\s*:|Timing\s*:|Synopsis\s*:", header, maxsplit=1, flags=re.I)[0]
    header = re.sub(r"\s+", " ", header[:1500]).strip().upper()
    header = re.sub(r"\bANTIGUA\s+AND\s+BARBUDA\s+METEOROLOGICAL\s+SERVICES\b", "", header)
    scope_match = re.search(r"\b(?:FOR|AFFECTING|AFFECTED\s+AREAS?\s*:)\s+(.+)", header)
    if scope_match:
        scope = re.split(r"[.;]|\b(?:WHILE|BUT(?!\s+NOT)|RESIDENTS|SHOULD|WILL)\b", scope_match[1])[0]
    else:
        # A bare region heading is accepted only when no non-geographic text
        # remains after removing the product's own heading.
        scope = re.sub(r"\b(?:HIGH\s+SURF|SMALL\s+CRAFT)\s+(?:ADVISORY|WARNING)\b", "", header).strip(" :-.")
        if not re.fullmatch(r"(?:ANTIGUA|BARBUDA)(?:\s*(?:AND|&|,)\s*(?:ANTIGUA|BARBUDA))*", scope):
            return []
    exclusions = re.split(r"\b(?:EXCEPT|EXCLUDING|EXCLUDES|OTHER\s+THAN|BUT\s+NOT)\b", scope, maxsplit=1)
    islands = _islands(exclusions[0])
    if len(exclusions) > 1:
        islands = [island for island in islands if island not in _islands(exclusions[1])]
    return islands


def parse_marine_cancellations(text, issue_end, product_name):
    """Return islands with an affirmative, current cancellation of this product."""
    if product_name not in MARINE_PRODUCTS or not isinstance(issue_end, int) or not 0 <= issue_end <= len(text):
        return []
    header = re.split(r"\b(?:Timing|Synopsis)\s*:", text[issue_end:], maxsplit=1, flags=re.I)[0]
    header = re.sub(r"\s+", " ", header[:2500]).upper()
    product_pattern = re.compile(r"\b" + r"\s+".join(map(re.escape, product_name.upper().split())) + r"\b")
    other_product = re.compile(r"\b(?:HIGH\s+SURF|SMALL\s+CRAFT)\s+(?:ADVISORY|WARNING)\b")
    cancelled = set()
    for sentence in re.split(r"[.;]", header):
        for cancellation in _AFFIRMATIVE_CANCEL.finditer(sentence):
            if re.search(r"\b(?:NOT|NEVER|IF|UNLESS|WHEN|WILL|WOULD|COULD|MAY|MIGHT|SHOULD)\b", sentence[:cancellation.end()]):
                continue
            products = list(other_product.finditer(sentence))
            before = [product for product in products if product.start() < cancellation.start()]
            after = [product for product in products if product.start() >= cancellation.end()]
            product = before[-1] if before else after[0] if after else None
            if product is None or not product_pattern.fullmatch(product.group()):
                continue
            beginning = min(product.start(), cancellation.start())
            clause = re.split(r"\b(?:WHILE|BUT(?!\s+NOT))\b", sentence[beginning:])[0]
            following = other_product.search(clause, product.end() - beginning)
            if following:
                clause = clause[:following.start()]
            scopes = re.split(r"\b(?:EXCEPT|EXCLUDING|EXCLUDES|OTHER\s+THAN|BUT\s+NOT)\b", clause, maxsplit=1)
            islands = _islands(scopes[0])
            if len(scopes) > 1:
                islands = [island for island in islands if island not in _islands(scopes[1])]
            cancelled.update(islands)
    return [island for island in ("Antigua", "Barbuda") if island in cancelled]


def _label(kind, level, islands):
    kind = re.sub(r"\s+", " ", kind).replace("FLASHFLOOD", "FLASH FLOOD").title()
    return f"{kind} {level.title()} — {' and '.join(islands)}"


def _alert_parts(names):
    parts = set()
    for name in names:
        product, _, area = name.partition(" — ")
        for island in ("Antigua", "Barbuda"):
            if island in area:
                parts.add((product, island))
    return parts


def _group_alerts(parts):
    products = {}
    for product, island in sorted(parts):
        products.setdefault(product, []).append(island)
    return [f"{product} — {' and '.join(islands)}" for product, islands in products.items()]


def _check(state, reason, url, **values):
    return {"state": state, "active": state == "active", "reason": reason, "url": url, "alerts": [], **values}


def _operative_matches(text):
    for match in _OPERATIVE.finditer(text):
        prefix = re.split(r"[.;]", text[max(0, match.start() - 110):match.start()])[-1]
        if not re.search(r"\b(?:IF|WHEN|UNLESS|EXAMPLE|MEANS|NO|NOT)\b", prefix):
            yield match


def parse_statement(raw, url, now):
    """Parse an official HTML statement; ambiguous text deliberately stays unknown."""
    text = _text(raw)
    issued = _issue(text)
    if issued is None:
        return _check("unknown", "issue_date_unreadable", url)
    details = {"issued": _iso(issued)}
    if issued > now:
        return _check("unknown", "future_issue", url, **details)
    operative = list(_operative_matches(text))
    validity = " ".join(re.split(r"[.;]", text[match.start():match.end() + 300])[0] for match in operative)
    until = re.search(r"\b(?:UNTIL|EXPIRES?(?:\s+AT)?)\s+(.{1,180})", validity)
    expiry = None
    if until:
        fragment = re.split(r"[.;]|\b(?:SYNOPSIS|POTENTIAL IMPACTS|INSTRUCTIONS)\b", until[1])[0]
        expiry = _relative_time(fragment, issued)
        if expiry is None and not re.match(r"FURTHER NOTICE\b", fragment):
            return _check("unknown", "timing_unreadable", url, **details)
    if expiry is not None:
        details["expires"] = _iso(expiry)
        if expiry < issued:
            return _check("unknown", "invalid_timing", url, **details)
        if now >= expiry:
            return _check("inactive", "expired", url, **details)
    # Alert validity is separate from forecast conditions later in the bulletin.
    start_match = None
    for declaration in operative:
        clause = re.split(r"[.;]", text[declaration.end():declaration.end() + 300])[0]
        candidate = re.search(r"\b(?:FROM|STARTING|EFFECTIVE)\s+(?:AT\s+)?(\d.{0,100})", clause)
        if candidate and not re.search(r"\b(?:CONDITIONS|EXPECTED|FORECAST|POSSIBLE|WINDS|RAINFALL)\b", clause[:candidate.start()]):
            start_match = candidate
            break
    if start_match:
        starts = _relative_time(re.split(r"[.;]|\bUNTIL\b", start_match[1])[0], issued)
        if starts is None:
            return _check("unknown", "timing_unreadable", url, **details)
        details["starts"] = _iso(starts)
        if expiry is not None and starts > expiry:
            return _check("unknown", "invalid_timing", url, **details)
        if starts > now:
            return _check("inactive", "not_started", url, **details)
    fresh_until = expiry or issued + timedelta(hours=12)
    update = re.search(r"\bTHE NEXT\s+(?:ADVISORY|UPDATE|BULLETIN)\b.{0,75}?\b(?:AT|BY)\s+(.{1,90})", text)
    if update:
        update_at = _relative_time(update[1], issued, next_update=True)
        if update_at and update_at > issued:
            details["next_update"] = _iso(update_at)
            fresh_until = min(fresh_until, update_at)
    details["fresh_until"] = _iso(fresh_until)
    if now >= fresh_until:
        return _check("unknown", "stale_bulletin", url, **details)
    declarations, foreign = [], False
    for match in operative:
        scope = text[match.end():match.end() + 300]
        scope = re.split(r"[.;]|\b(?:WHILE|UNTIL|FROM|STARTING|EFFECTIVE)\b", scope)[0]
        scope = re.split(r"\bAND\s+(?:ANTIGUA|BARBUDA)\s+RESIDENTS\s+(?:SHOULD|ARE|MUST|WILL)\b", scope)[0]
        next_product = _NEXT_PRODUCT.search(scope)
        if next_product:
            scope = scope[:next_product.start()]
        exclusions = re.split(r"\b(?:EXCEPT|EXCLUDING|EXCLUDES|OTHER THAN|BUT NOT)\b", scope, maxsplit=1)
        islands = _islands(exclusions[0])
        if len(exclusions) > 1:
            islands = [island for island in islands if island not in _islands(exclusions[1])]
        if islands:
            declarations.append(_label(match["kind"], match["level"], islands))
        else:
            foreign = True
    cancelled = []
    # A cancellation must name the product and local scope in the same sentence.
    for sentence in re.split(r"[.;]", text):
        for cancellation in _AFFIRMATIVE_CANCEL.finditer(sentence):
            prefix = sentence[:cancellation.end()]
            if re.search(r"\b(?:NOT|NEVER|IF|UNLESS|WHEN|WILL|WOULD|COULD|MAY|MIGHT|SHOULD)\b", prefix):
                continue
            products = list(re.finditer(_PRODUCT, sentence, re.I))
            before = [product for product in products if product.start() < cancellation.start()]
            after = [product for product in products if product.start() >= cancellation.end()]
            product = before[-1] if before else after[0] if after else None
            if product:
                # Keep later clauses/products from donating a second locality.
                operative_start = min(cancellation.start(), product.start())
                clause = re.split(r"\b(?:WHILE|BUT)\b", sentence[operative_start:])[0]
                next_product = _NEXT_PRODUCT.search(clause, product.end() - operative_start)
                if next_product:
                    clause = clause[:next_product.start()]
                islands = _islands(clause)
                if islands:
                    cancelled.append(_label(product["kind"], product["level"], islands))
    declarations = _group_alerts(_alert_parts(declarations) - _alert_parts(cancelled))
    if declarations:
        return _check("active", "active", url, alerts=declarations, cancelled_alerts=cancelled, **details)
    if cancelled:
        return _check("inactive", "cancelled", url, cancelled_alerts=cancelled, **details)
    if foreign:
        return _check("inactive", "not_for_antigua_or_barbuda", url, **details)
    negative = re.search(r"\bNO\s+(?:TROPICAL STORM|HURRICANE|FLASH FLOOD|FLOOD)?\s*(?:WATCH(?:ES)?|WARNINGS?|ADVISOR(?:Y|IES))(?:\s+OR\s+(?:WATCH(?:ES)?|WARNINGS?|ADVISOR(?:Y|IES)))*\s+(?:(?:IS|ARE)\s+)?(?:CURRENTLY\s+)?IN EFFECT\s+FOR\s+([^.;]+)", text)
    if negative and _islands(negative[1]):
        return _check("inactive", "none_in_effect", url, **details)
    return _check("unknown", "no_current_declaration", url, **details)


def _fetch(url):
    request = Request(url, headers={"User-Agent": "SeaPoint-OfficialAlerts/1.0"})
    with urlopen(request, timeout=8) as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("official bulletin exceeds size limit")
    return body


class OfficialAlertService:
    """Five-minute, singleflight aggregation over the supported official sources."""
    def __init__(self, marine_loader, fetcher=None, clock=None, cache_ttl=300):
        self.marine_loader = marine_loader
        self.fetcher = fetcher or _fetch
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._snapshot = None
        self._cached_at = None
        self._cancellations = {}

    def _statement(self, url, now):
        try:
            return parse_statement(self.fetcher(url), url, now)
        except Exception:
            return _check("unknown", "source_error", url)

    def _marine(self, now):
        try:
            loaded = self.marine_loader()
            loaded = dict(loaded)
        except Exception:
            loaded = {}
        checks = {}
        for name, canonical in MARINE_PRODUCTS.items():
            value = loaded.get(name)
            if not isinstance(value, dict):
                checks["marine:" + name] = _check("unknown", "source_error", canonical)
                continue
            areas = value.get("area_checks")
            if isinstance(areas, dict) and areas:
                entries = [("marine:" + name + ":" + island, dict(areas[island], locations=[island])) for island in ("Antigua", "Barbuda") if isinstance(areas.get(island), dict)]
                if not entries:
                    entries = [("marine:" + name, {"active": False, "reason": "locations_unreadable"})]
            else:
                entries = [("marine:" + name, value)]
            for source_key, entry in entries:
                result = dict(entry)
                reason = str(result.get("reason", "unknown"))
                url = result.get("url") or value.get("url") or canonical
                expiry, start = _from_iso(result.get("expires")), _from_iso(result.get("starts"))
                state = "unknown"
                if result.get("active") is True:
                    state = "active"
                    if expiry is not None and now >= expiry:
                        state, reason = "inactive", "expired"
                    elif start is not None and start > now:
                        state, reason = "inactive", "not_started"
                elif reason in {"expired", "not_started", "not_for_antigua_or_barbuda", "not_listed", "not_currently_listed", "not_in_effect", "inactive", "cancelled", "discontinued", "none_in_effect"}:
                    state = "inactive"
                label = name
                if "locations" in result:
                    locations = [island for island in ("Antigua", "Barbuda") if island in (result.get("locations") or [])]
                    if locations:
                        label = f"{name} — {' and '.join(locations)}"
                    elif state == "active":
                        state, reason = "unknown", "locations_unreadable"
                result.update(state=state, active=state == "active", reason=reason, url=url, alerts=[label] if state == "active" else [])
                checks[source_key] = result
        return checks

    def snapshot(self):
        # Holding this lock during the bounded parallel refresh makes concurrent
        # dashboard requests share one refresh instead of refetching each PDF.
        with self._lock:
            now = _aware(self.clock())
            if self._snapshot is not None and 0 <= (now - self._cached_at).total_seconds() < self.cache_ttl:
                bounds = [_from_iso(value.get(field)) for value in self._snapshot["checked"].values() if value.get("alerts") for field in ("expires", "fresh_until")]
                if all(bound is None or now < bound for bound in bounds):
                    return deepcopy(self._snapshot)
            with ThreadPoolExecutor(max_workers=5) as executor:
                marine = executor.submit(self._marine, now)
                futures = {key: executor.submit(self._statement, url, now) for key, url in SOURCES.items()}
                checked = marine.result()
                checked.update({key: future.result() for key, future in futures.items()})
            previous = (self._snapshot or {}).get("checked", {})
            # A failed PDF has no per-island checks. Preserve its prior source
            # identities as unknown so bounded retention still applies.
            for key, old in previous.items():
                if key in checked or not key.startswith("marine:") or not key.endswith((":Antigua", ":Barbuda")):
                    continue
                base = key.rsplit(":", 1)[0]
                if checked.get(base, {}).get("state") == "unknown":
                    checked[key] = _check("unknown", checked[base]["reason"], old["url"])
            for result in checked.values():
                result["checked_at"] = _iso(now)
            for key, result in checked.items():
                old = previous.get(key, {})
                if result["state"] != "unknown" or not old.get("alerts"):
                    continue
                limits = [_from_iso(old.get(field)) for field in ("expires", "fresh_until")]
                limits = [limit for limit in limits if limit is not None]
                # A cached alert is retained only with a known, still-valid bound.
                if limits and now < min(limits):
                    result.update(alerts=list(old["alerts"]), cached=True)
                    for field in ("issued", "starts", "expires", "fresh_until", "checked_at"):
                        if old.get(field):
                            result[field] = old[field]
            alerts, links, alert_sources = [], {}, {}
            for result in checked.values():
                for part in _alert_parts(result.get("cancelled_alerts", [])):
                    self._cancellations[part] = max(self._cancellations.get(part, ""), result.get("issued", ""))
            # Resolve each island independently so a newer Antigua cancellation
            # can remove Antigua without removing a still-current Barbuda alert.
            winners = {}
            for key, result in sorted(checked.items(), key=lambda item: item[1].get("issued", "")):
                for part in _alert_parts(result.get("alerts", [])):
                    if self._cancellations.get(part, "") >= result.get("issued", "") and part in self._cancellations:
                        continue
                    winners[part] = key
                # Marine alert labels have no island suffix.
                for name in result.get("alerts", []):
                    if " — " not in name:
                        winners[(name, "")] = key
            by_source = {}
            for (product, island), key in winners.items():
                by_source.setdefault(key, []).append((product, island))
            for key, result in checked.items():
                selected = by_source.get(key, [])
                names = _group_alerts({part for part in selected if part[1]})
                names += [product for product, island in selected if not island]
                if result["state"] == "active" and not names:
                    result.update(state="inactive", active=False, reason="superseded_by_newer_statement")
                result["alerts"] = names
                for name in names:
                    alerts.append(name)
                    links[name], alert_sources[name] = result["url"], key
            known = sum(result["state"] != "unknown" for result in checked.values())
            status = "ready" if known == len(checked) else "partial" if known else "unavailable"
            snapshot = {
                "alerts": alerts, "links": links, "alert_sources": alert_sources,
                "status": status, "checked_at": _iso(now), "checked": checked,
                "coverage": {
                    "region": "Antigua and Barbuda", "categories": ["marine", "tropical_cyclone", "flash_flood"],
                    "sources_total": len(checked), "sources_verified": known,
                    "sources_unknown": len(checked) - known,
                },
            }
            self._snapshot, self._cached_at = snapshot, now
            return deepcopy(snapshot)
