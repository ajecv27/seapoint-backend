"""SeaPoint Caribbean land-avoidance routing (prototype; not for navigation)."""

import heapq
import json
import math
import os
import time
import threading

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from shapely.geometry import LineString, Point, shape
from shapely.strtree import STRtree


ROUTING_BUILD = "seapoint-hosted-caribbean-v1"

_ROUTE_METRICS = threading.local()

from .coast_data import load_coast

COVERAGE = (-94.0, 5.0, -55.0, 34.0)

EDGE_CLEARANCE = 0.0015
MIN_CLEARANCE = 0.000006

MAX_SNAP_METRES = 75

DIRECTIONS = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
)


LAND = None
OSM_LAND = None
DATASET = None
_DEADLINE = None


class RouteTimeout(Exception):
    pass


def check_deadline():
    if _DEADLINE is not None and time.monotonic() > _DEADLINE:
        raise RouteTimeout('Route calculation timed out. Try a shorter route or move the endpoints into open water.')


def initialize():
    global LAND, OSM_LAND, DATASET
    geometries, osm, manifest = load_coast()
    LAND = STRtree(geometries)
    OSM_LAND = STRtree(osm)
    DATASET = manifest
    return manifest


from shapely.prepared import prep

@lru_cache(maxsize=2048)
def _prepared_coastline(index):
    return prep(LAND.geometries[int(index)])

def on_land(point):
    check_deadline()
    g = Point(point)
    return any(_prepared_coastline(i).covers(g) for i in LAND.query(g))

def clear_segment(start, finish, clearance=0.0):
    check_deadline()
    line = LineString((start, finish))
    tested = line.buffer(max(clearance, MIN_CLEARANCE))
    return not any(_prepared_coastline(i).intersects(tested) for i in LAND.query(tested))

def nautical_miles(start, finish):
    lon1, lat1 = start
    lon2, lat2 = finish

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(delta_lon / 2) ** 2
    )

    return (
        3440.065
        * 2
        * math.asin(min(1, math.sqrt(value)))
    )


def path_length(points):
    return sum(
        nautical_miles(start, finish)
        for start, finish in zip(points, points[1:])
    )


def endpoint_on_water(point, label):
    """
    Correct small coastline mapping discrepancies.

    A point identified as land may be moved to nearby
    mapped water, but no route is drawn through that land.
    """

    if not on_land(point):
        return point, 0.0

    latitude = math.radians(point[1])

    cos_lat = max(
        0.1,
        math.cos(latitude),
    )

    search_distances = (
        10,
        20,
        35,
        50,
        60,
        MAX_SNAP_METRES,
    )

    for metres in search_distances:
        candidates = []

        for number in range(48):
            angle = number * math.tau / 48

            candidate = (
                point[0]
                + math.cos(angle)
                * metres
                / (111320 * cos_lat),

                point[1]
                + math.sin(angle)
                * metres
                / 111132,
            )

            if not on_land(candidate):
                candidates.append(candidate)

        if candidates:
            chosen = min(
                candidates,
                key=lambda candidate: nautical_miles(
                    point,
                    candidate,
                ),
            )

            adjustment = (
                nautical_miles(point, chosen) * 1852
            )

            return chosen, round(adjustment, 1)

    raise ValueError(
        f"{label} is on mapped land, and no nearby "
        f"water was found within {MAX_SNAP_METRES} m. "
        "Select a point in open water."
    )


def simplify_route(points):
    """Remove redundant shape points without permitting land intersections.

    The previous farthest-first loop could perform O(n^2) coastline
    intersection tests, particularly for shoreline connectors.  This
    iterative split procedure normally uses far fewer tests; every
    shortcut still requires the existing land-intersection check.
    """
    if len(points) < 3:
        return list(points)

    # Remove any duplicate adjacent points, preserving both endpoints.
    cleaned = [points[0]]
    for point in points[1:]:
        if point != cleaned[-1]:
            cleaned.append(point)

    if len(cleaned) < 3:
        return cleaned

    # Precompute which raw legs cannot meet the offshore buffer.
    # A prefix sum allows each candidate span to be checked in O(1).
    close_prefix = [0]
    for a, b in zip(cleaned, cleaned[1:]):
        close_prefix.append(
            close_prefix[-1] + int(not clear_segment(a, b, EDGE_CLEARANCE))
        )

    keep = {0, len(cleaned) - 1}
    stack = [(0, len(cleaned) - 1)]

    while stack:
        left, right = stack.pop()
        if right - left <= 1:
            continue

        # Preserve the original open-water clearance whenever possible.
        if clear_segment(cleaned[left], cleaned[right], EDGE_CLEARANCE):
            continue

        # The original routing engine permits close-shore connectors at
        # MIN_CLEARANCE and validates every segment at this threshold.
        # Restrict relaxed shortcuts to portions containing one or more
        # existing close-shore connectors, so routine offshore legs
        # keep the stricter clearance.
        has_close_shore_leg = (close_prefix[right] > close_prefix[left])

        if has_close_shore_leg and clear_segment(
            cleaned[left], cleaned[right], 0.0
        ):
            continue

        # Divide by greatest lateral deviation from the attempted chord.
        # If the path is almost collinear but the chord is obstructed,
        # split near the midpoint so progress is guaranteed.
        ax, ay = cleaned[left]
        bx, by = cleaned[right]
        latitude = math.radians((ay + by) / 2.0)
        scale_lon = max(0.1, math.cos(latitude))
        dx = (bx - ax) * scale_lon
        dy = by - ay
        denominator = math.hypot(dx, dy)

        split = (left + right) // 2
        largest = -1.0
        for i in range(left + 1, right):
            px = (cleaned[i][0] - ax) * scale_lon
            py = cleaned[i][1] - ay
            deviation = (
                abs(px * dy - py * dx) / denominator
                if denominator > 1e-12 else math.hypot(px, py)
            )
            if deviation > largest:
                largest = deviation
                split = i

        keep.add(split)
        stack.append((split, right))
        stack.append((left, split))

    result = [cleaned[i] for i in sorted(keep)]

    # Fail closed: no optimization may introduce a land intersection.
    if any(not clear_segment(a, b) for a, b in zip(result, result[1:])):
        raise ValueError('Simplified route failed shoreline validation')

    return result


def astar_route(
    start,
    finish,
    step,
    margin,
    *,
    clearance=EDGE_CLEARANCE,
    max_cells=145000,
    fine_connectors=False,
):
    min_lon = max(
        COVERAGE[0],
        min(start[0], finish[0]) - margin,
    )

    max_lon = min(
        COVERAGE[2],
        max(start[0], finish[0]) + margin,
    )

    min_lat = max(
        COVERAGE[1],
        min(start[1], finish[1]) - margin,
    )

    max_lat = min(
        COVERAGE[3],
        max(start[1], finish[1]) + margin,
    )

    nx = math.ceil(
        (max_lon - min_lon) / step
    ) + 1

    ny = math.ceil(
        (max_lat - min_lat) / step
    ) + 1

    if nx * ny > max_cells:
        return None

    def coordinates(node):
        return (
            min_lon + node[0] * step,
            min_lat + node[1] * step,
        )

    @lru_cache(maxsize=180000)
    def valid(node):
        return (
            0 <= node[0] < nx
            and 0 <= node[1] < ny
            and not on_land(coordinates(node))
        )

    def nearby(point):
        gx = math.floor(
            (point[0] - min_lon) / step
        )

        gy = math.floor(
            (point[1] - min_lat) / step
        )

        radius = 8 if fine_connectors else 5

        candidates = (
            (i, j)
            for i in range(
                gx - radius,
                gx + radius + 2,
            )
            for j in range(
                gy - radius,
                gy + radius + 2,
            )
            if valid((i, j))
        )

        return sorted(
            candidates,
            key=lambda node: nautical_miles(
                coordinates(node),
                point,
            ),
        )

    def terminal_links(point, backwards=False):
        candidates = nearby(point)

        direct = {}

        for node in candidates:
            target = coordinates(node)

            if clear_segment(point, target):
                direct[node] = [
                    point,
                    target,
                ]

                if len(direct) == 24:
                    break

        if direct and not fine_connectors:
            return {
                node: (
                    list(reversed(path))
                    if backwards
                    else path
                )
                for node, path in direct.items()
            }

        if fine_connectors:
            count = 0
            attempted = 0

            for node in candidates[:24]:
                if node in direct:
                    continue

                if count >= 2 or attempted >= 8:
                    break

                attempted += 1

                target = coordinates(node)

                fine = None

                for resolution in (
                    0.00035,
                    0.0002,
                ):
                    fine = astar_route(
                        point,
                        target,
                        resolution,
                        0.005,
                        clearance=0.0,
                        max_cells=110000,
                    )

                    if fine:
                        break

                if fine:
                    direct[node] = fine
                    count += 1

        return {
            node: (
                list(reversed(path))
                if backwards
                else path
            )
            for node, path in direct.items()
        }

    start_links = terminal_links(start)

    end_links = terminal_links(
        finish,
        backwards=True,
    )

    if not start_links or not end_links:
        return None

    # Cache each undirected grid edge only once. A* examines many edges
    # in both directions; this halves repeated Shapely checks for them.
    @lru_cache(maxsize=250000)
    def _edge_clear_sorted(a, b):
        return clear_segment(
            coordinates(a),
            coordinates(b),
            clearance,
        )

    def edge_clear(a, b):
        return _edge_clear_sorted(*(a, b) if a < b else (b, a))

    START = (-1, -1)
    END = (-2, -2)

    distances = {
        START: 0.0,
    }

    previous = {}

    queue = [
        (
            nautical_miles(start, finish),
            0.0,
            START,
        )
    ]

    expanded = 0

    while queue and expanded < max_cells:
        check_deadline()
        _, cost, current = heapq.heappop(queue)

        if cost > distances.get(
            current,
            float("inf"),
        ) + 1e-8:
            continue

        if current == END:
            chain = []

            while current != START:
                chain.append(current)
                current = previous[current]

            chain.reverse()

            grid_nodes = chain[:-1]

            first = grid_nodes[0]
            last = grid_nodes[-1]

            route = list(start_links[first])

            for node in grid_nodes[1:]:
                route.append(
                    coordinates(node)
                )

            route.extend(
                end_links[last][1:]
            )

            return route

        expanded += 1

        if current == START:
            adjacent = [
                (
                    node,
                    path_length(path),
                )
                for node, path in start_links.items()
            ]

        else:
            adjacent = []

            if current in end_links:
                adjacent.append(
                    (
                        END,
                        path_length(
                            end_links[current]
                        ),
                    )
                )

            x, y = current

            for dx, dy in DIRECTIONS:
                neighbor = (
                    x + dx,
                    y + dy,
                )

                if valid(neighbor) and edge_clear(
                    current,
                    neighbor,
                ):
                    adjacent.append(
                        (
                            neighbor,
                            nautical_miles(
                                coordinates(current),
                                coordinates(neighbor),
                            ),
                        )
                    )

        for neighbor, edge_distance in adjacent:
            new_cost = cost + edge_distance

            if new_cost < distances.get(
                neighbor,
                float("inf"),
            ):
                distances[neighbor] = new_cost

                previous[neighbor] = current

                heuristic = (
                    0.0
                    if neighbor == END
                    else nautical_miles(
                        coordinates(neighbor),
                        finish,
                    )
                )

                heapq.heappush(
                    queue,
                    (
                        new_cost + heuristic,
                        new_cost,
                        neighbor,
                    ),
                )

    return None


def calculate_route(start, finish):
    _ROUTE_METRICS.data = None
    total_start = time.perf_counter()
    search_start = total_start
    search_elapsed = 0.0
    simplify_elapsed = 0.0
    attempts = 0

    for point in (start, finish):
        if not (
            COVERAGE[0] <= point[0] <= COVERAGE[2]
            and COVERAGE[1] <= point[1] <= COVERAGE[3]
        ):
            raise ValueError(
                "Point outside Caribbean coverage"
            )

    if start == finish:
        raise ValueError(
            "Choose two different locations"
        )

    if on_land(start) or on_land(finish):
        raise ValueError(
            "Point is on mapped land"
        )

    if clear_segment(start, finish, EDGE_CLEARANCE):
        points = [start, finish]

    else:
        span = max(
            abs(start[0] - finish[0]),
            abs(start[1] - finish[1]),
        )

        points = None

        # Use higher resolution for short coastal routes.
        if span <= 0.035:
            for resolution in (
                0.0002,
                0.00035,
                0.00065,
            ):
                attempts += 1
                points = astar_route(
                    start,
                    finish,
                    resolution,
                    0.006,
                    clearance=0.0,
                    max_cells=115000,
                )

                if points:
                    break

        if not points:
            step = max(
                0.003,
                min(
                    0.04,
                    span / 120,
                ),
            )

            # Prefer fine shoreline connectors after the normal fast path.
            # This preserves the original fallback order and land checks.
            near_coast = (
                not clear_segment(start, start, EDGE_CLEARANCE)
                or not clear_segment(finish, finish, EDGE_CLEARANCE)
            )

            prioritized = (True, 0.3) if near_coast else None
            tried = set()
            attempt_details = []

            def attempt(fine, margin):
                nonlocal attempts
                key = (fine, margin)
                if key in tried:
                    return None
                tried.add(key)
                attempts += 1
                started = time.perf_counter()
                candidate = astar_route(
                    start,
                    finish,
                    step,
                    margin,
                    fine_connectors=fine,
                )
                attempt_details.append({
                    "fine": fine,
                    "margin": margin,
                    "seconds": round(time.perf_counter() - started, 3),
                    "found": candidate is not None,
                })
                return candidate

            if prioritized is not None:
                # Preserve the normal fast path for uncomplicated coastal
                # routes. Escalate directly to the known successful fine
                # configuration only when that fast path fails.
                points = attempt(False, 0.12)
                if not points:
                    points = attempt(*prioritized)

            if not points:
                for use_fine_connectors in (False, True):
                    for margin in (0.12, 0.3, 0.65, 1.3, 2.5):
                        points = attempt(use_fine_connectors, margin)
                        if points:
                            break
                    if points:
                        break

        if not points:
            raise ValueError(
                "No water-only route found "
                "within the search area"
            )

        search_elapsed = time.perf_counter() - search_start
        simplify_start = time.perf_counter()
        points = simplify_route(points)
        simplify_elapsed = time.perf_counter() - simplify_start

    validation_start = time.perf_counter()
    for a, b in zip(
        points,
        points[1:],
    ):
        if not clear_segment(a, b):
            raise ValueError(
                "Route failed shoreline validation"
            )
    validation_elapsed = time.perf_counter() - validation_start

    _ROUTE_METRICS.data = {
        "search_s": round(search_elapsed, 3),
        "simplify_s": round(simplify_elapsed, 3),
        "validation_s": round(validation_elapsed, 3),
        "calculate_s": round(time.perf_counter() - total_start, 3),
        "attempts": attempts,
        "search_attempt_details": locals().get("attempt_details", []),
    }

    if os.getenv("SEAPOINT_ROUTE_TIMING", "1") == "1":
        print(
            "SeaPoint route timing: "
            f"search={search_elapsed:.2f}s "
            f"simplify={simplify_elapsed:.2f}s "
            f"total={time.perf_counter() - total_start:.2f}s "
            f"attempts={attempts} "
            f"points={len(points)}",
            flush=True,
        )

    return points


def response_for(start, finish):
    response_start = time.perf_counter()
    adjusted_start, start_offset = endpoint_on_water(
        start,
        "Start point",
    )

    adjusted_finish, finish_offset = endpoint_on_water(
        finish,
        "Destination",
    )

    if adjusted_start == adjusted_finish:
        raise ValueError(
            "Choose two different locations"
        )

    endpoints_elapsed = time.perf_counter() - response_start

    points = calculate_route(
        adjusted_start,
        adjusted_finish,
    )

    shift_note = (
        " Near-shore point(s) were moved "
        "slightly to mapped water."
        if start_offset or finish_offset
        else ""
    )

    return {
        "status": "ok",
        "routing_build": ROUTING_BUILD,
        "timing": {
            "endpoints_s": round(endpoints_elapsed, 3),
            **(_ROUTE_METRICS.data or {}),
            "request_s": round(time.perf_counter() - response_start, 3),
        },
        "mode": "land-avoidance-prototype",
        "region": "caribbean",
        "coastline": "GSHHG full resolution plus Caribbean OpenStreetMap",
        "depth_checked": False,
        "coastline_dataset": DATASET["id"],
        "distance_nm": round(
            path_length(points),
            2,
        ),
        "points": [
            {
                "lat": round(lat, 7),
                "lon": round(lon, 7),
            }
            for lon, lat in points
        ],
        "geojson": {
            "type": "LineString",
            "coordinates": [
                [
                    round(lon, 7),
                    round(lat, 7),
                ]
                for lon, lat in points
            ],
        },
        "adjusted_start_m": start_offset,
        "adjusted_destination_m": finish_offset,
        "warning": (
            "Land-avoidance prototype only. "
            "Not suitable for vessel navigation. "
            "Depths, reefs, channels and hazards "
            "are not checked."
            + shift_note
        ),
    }


def route(start, finish, *, seconds=20.0):
    """Preserve the original planner, then validate the exact emitted points."""
    global _DEADLINE
    if LAND is None or OSM_LAND is None:
        raise RuntimeError('Coastline data is not initialized')
    for lon, lat in (start, finish):
        if not (math.isfinite(lon) and math.isfinite(lat) and
                COVERAGE[0] <= lon <= COVERAGE[2] and COVERAGE[1] <= lat <= COVERAGE[3]):
            raise ValueError('Choose start and destination within Caribbean routing coverage')
    _DEADLINE = time.monotonic() + seconds
    try:
        result = response_for(start, finish)
        points = [(p['lon'], p['lat']) for p in result['points']]
        if not 2 <= len(points) <= 4096 or len(set(points)) < 2:
            raise ValueError('Route could not be validated')
        for point in points:
            if not (COVERAGE[0] <= point[0] <= COVERAGE[2] and COVERAGE[1] <= point[1] <= COVERAGE[3]):
                raise ValueError('Route exits validated Caribbean coastline coverage')
        for a, b in zip(points, points[1:]):
            check_deadline()
            if not clear_segment(a, b):
                raise ValueError('Route failed shoreline validation')
            segment = LineString((a, b))
            if any(OSM_LAND.geometries[int(i)].intersects(segment) for i in OSM_LAND.query(segment)):
                raise ValueError('Route crosses mapped land; select different points')
        return result
    finally:
        _DEADLINE = None
