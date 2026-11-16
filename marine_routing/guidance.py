"""Live, forward-only guidance using the same coast checks as route planning."""
from functools import lru_cache
import math
import time

from shapely.geometry import LineString
from . import engine

VERSION = 'live-coast-guidance-v1'


def projection(position, a, b):
    sx = 111320 * math.cos(math.radians(position[1]))
    sy = 111132
    dx, dy = (b[0]-a[0])*sx, (b[1]-a[1])*sy
    px, py = (position[0]-a[0])*sx, (position[1]-a[1])*sy
    t = max(0, min(1, (px*dx+py*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
    return math.hypot(px-t*dx, py-t*dy)


def match_leg(position, points, minimum, accuracy):
    """Prefer the earliest equally close segment; never rewind past saved progress."""
    distances = [(projection(position, a, b), i) for i, (a, b) in
                 enumerate(zip(points, points[1:])) if i >= minimum]
    closest = min(d for d, _ in distances)
    tolerance = max(12, accuracy * 1.5) if closest <= 150 else max(100, accuracy * 2)
    return next(i for d, i in distances if d <= closest + tolerance)


def clear(a, b, radius=0):
    # The buffer certifies small origin movements, including the raw GPS point.
    degrees = radius / (111000 * math.cos(math.radians(max(abs(a[1]), abs(b[1])))))
    if not engine.clear_segment(a, b, degrees):
        return False
    shape = LineString((a, b)).buffer(max(degrees, engine.MIN_CLEARANCE))
    return not any(engine.OSM_LAND.geometries[int(i)].intersects(shape)
                   for i in engine.OSM_LAND.query(shape))


@lru_cache(maxsize=24)
def checked_path(points):
    for a, b in zip(points, points[1:]):
        engine.check_deadline()
        if not clear(a, b):
            raise ValueError('Guidance path crosses mapped land; calculate a new route')
    return points


def guidance(position, planned, minimum, accuracy, previous=()):
    engine._DEADLINE = time.monotonic() + 18
    try:
        checked_path(planned)
        leg = match_leg(position, planned, minimum, accuracy)
        radius = max(15, min(35, accuracy * 1.5))
        # Consume nearby waypoints, including multiple short legs in one fix.
        while leg < len(planned)-2 and engine.nautical_miles(position, planned[leg+1])*1852 <= radius:
            leg += 1
        arrived = (leg == len(planned)-2 and
                   engine.nautical_miles(position, planned[-1])*1852 <= radius and
                   clear(position, planned[-1]))
        points = None
        mode = 'rejoined'
        if clear(position, planned[leg+1]):
            points = (position,) + planned[leg+1:]
        elif previous and previous[-1] == planned[-1]:
            checked_path(previous)
            old_leg = match_leg(position, previous, 0, accuracy)
            while old_leg < len(previous)-2 and engine.nautical_miles(position, previous[old_leg+1])*1852 <= radius:
                old_leg += 1
            if clear(position, previous[old_leg+1]):
                points = (position,) + previous[old_leg+1:]
                mode = 'continuing'
        if points is None:
            result = engine.route(position, planned[-1], seconds=16)
            engine._DEADLINE = time.monotonic() + 2
            routed = tuple((p['lon'], p['lat']) for p in result['points'])
            if routed[-1] != planned[-1] or not clear(position, routed[0]):
                raise ValueError('Move the GPS position into mapped water for guidance')
            points = (position,) + routed
            mode = 'rerouted'
        # Drop duplicate zero-length vertices without modifying the stored plan.
        points = tuple(p for i, p in enumerate(points) if i == 0 or p != points[i-1])
        if len(points) == 1:
            points = points + points
        checked_path(points)
        origin_radius = next((r for r in (60, 30, 15, 5, 1)
                              if clear(points[0], points[1], r)), 0)
        return {'status': 'ok', 'guidance_version': VERSION,
                'coastline_dataset': engine.DATASET['id'],
                'coastline_policy': engine.COASTLINE_POLICY,
                'depth_checked': False, 'active_leg': leg, 'arrived': arrived,
                'mode': mode, 'origin_radius_m': origin_radius,
                'points': [list(p) for p in points]}
    finally:
        engine._DEADLINE = None
