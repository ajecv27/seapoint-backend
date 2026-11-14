# Hosted Caribbean routing

The existing Render service now serves the land-avoidance planner previously
running in the SeaPoint Docker containers. Phones use the same HTTPS backend
without USB, Docker or a local-network connection. No paid service is added.

## API and limits

* `GET /routing/health`: 200 when verified coastline data is ready, otherwise 503.
* `GET /route?start_lat=17.08&start_lon=-61.9&end_lat=17.08&end_lon=-61.65`
  returns the existing `{status, points, distance_nm, ...}` response.
* Coverage is longitude -94 to -55 and latitude 5 to 34. Outside this area the
  request fails explicitly. There is no direct-line fallback across land.
* One isolated worker performs searches; concurrent requests receive a bounded,
  retryable 429. Warmup returns a retryable 503. Deadline or worker failure does
  not block the weather HTTP server. Successful routes cache in memory for 15
  minutes, up to 64 entries. Route coordinates are omitted from access logs.
* Existing forecast endpoints remain available on demand. The published radar
  builds separately with `requirements-radar.txt`; coastline data is never
  downloaded by the phone or the hourly radar publisher.

This is a **land-avoidance prototype**, not validated marine navigation. It does
not check depth, reefs, channels, currents or vessel draft. Every response retains
`depth_checked: false` and the existing warning. Preserve that warning in the app.

## Coastline provenance

`coast_build/` records the reproducible download, clip and package process. The
immutable GitHub Release wheel is installed at build time using a SHA256-pinned
URL in `requirements.txt`. Startup checks its manifest, hashes, CRS, bounds,
record counts and geometry validity before enabling routing.

The package contains full-resolution GSHHG 2.3.7 level-1 land and OpenStreetMap
land polygons dated 13 November 2026, clipped to Caribbean coverage without
geometry simplification. Current detailed OSM outlines take precedence for
landmasses present in both datasets; unmatched GSHHG islands remain obstacles.
Unioning the old and new outline had incorrectly filled marina inlets, including
Jolly Harbour. This source policy applies throughout coverage, with no manually
carved harbour corridors. Every emitted segment is checked against the selected
coast and independently against the OSM land layer. Health and route responses
identify this policy as `osm-primary-gshhg-unmatched-v1`.

Coarse-grid connections must meet the existing offshore clearance. Near-shore
connectors expand their local search to find harbour entrances beyond the direct
endpoint box; endpoint adjustments must also meet the mandatory shoreline buffer.
The 75-metre maximum adjustment, route search budgets and final land checks remain.

OpenStreetMap data: © OpenStreetMap contributors, ODbL 1.0,
https://www.openstreetmap.org/copyright . GSHHG: Wessel and Smith, LGPL,
https://www.soest.hawaii.edu/pwessel/gshhg/ . Source digests, licence copies and
feature counts accompany the release. The phone update adds these credits to
the map attribution control.

## Deployment and validation

Source matching is precomputed in `marine_routing/coast_policy.json` so a sleeping
host does not repeat whole-region polygon intersections. Runtime verifies its
checksum, dataset digest, feature counts and indices before using it. CI compares
the complete selection against the original geometric predicates. Regenerate with
`python -m coast_build.policy_index` after changing the immutable source release,
then update the printed index digest in `coast_data.py`. Initialization is bounded
at 75 seconds to accommodate a throttled cold host; route deadlines are unchanged.
Health exposes a generic startup error code and worker logs omit coordinates.

Render continues using `pip install -r requirements.txt` and
`python cloud_server.py`. HTTP binds before the worker loads its geometry.
Free Render hosting can still sleep; first routing after inactivity may wait for
the service to wake. The client retries only explicitly transient warmup/busy
responses within a fixed budget. No background keep-alive is installed.

Run `python -m unittest discover -s tests` for existing weather and new routing
checks. `python -m unittest discover -s tests -p 'test_routing_coast_live.py'`
also exercises the installed release's actual coastlines when its data package
is available. Tests cover detours, rejected land endpoints, corrupt data,
timeouts, worker recovery and weather/radar responses while routing is loading.

The guarded `android-client/online-routing-update.ps1` changes only routing
connection code and map credits. It checks cloud health before writing, preserves
unrelated edits, backs up existing files and restores originals after a failed
write. Trip storage, navigation tracking and weather UI are unaffected.
