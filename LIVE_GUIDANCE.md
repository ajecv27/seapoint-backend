# Live navigation guidance

A vessel that bypasses early waypoints now matches the remaining planned segments instead of waiting indefinitely at leg one. The active course is calculated from the accepted live GPS fix to the next checked guidance point. The original plan, local black track, elapsed time and speed statistics remain separate.

`POST /routing/guidance` takes `position` and `planned` coordinates in `[longitude, latitude]` order, a forward-only `active_leg`, `accuracy_m` (0–50), and optional `previous` guidance points. It validates the original path and every live connector against the same detailed OSM/GSHHG coast used by `/route`. A blocked connector can continue a previous checked detour or calculate a fresh route to the original destination. Request bodies and private coordinates are not written to access logs; recorded trip tracks are never sent. Paths are bounded to 4,096 vertices and handled by the existing isolated, time/memory-bounded routing worker.

The reply includes `guidance_version: live-coast-guidance-v1`, `active_leg`, `arrived`, `points`, and `origin_radius_m`. The latter certifies a conservative water corridor around the first segment. The phone updates its line and live course inside that radius; after leaving it, losing fresh GPS, or receiving an incompatible response, it withholds the instruction until another coast check succeeds. Transient failures retry with a four-second backoff. A single installation has at most one guidance request in flight and never requests faster than once per second. Old replies cannot overwrite a stopped/new trip or move progress backwards.

This remains a land-avoidance prototype: `depth_checked` is false. Coast checks do not validate depths, reefs, channels, vessel draft, or other hazards. Existing in-app limitations remain visible. WorldTides subscriptions and weather behavior are unchanged.

## Client compatibility and validation

The updated Android client is required to use this endpoint. Existing clients keep their current behavior; `/route` remains compatible. Recorded track measurements are separate from live guidance.

Tests cover bypassed legs, ambiguous parallel segments, forward-only progress, blocked connectors and rerouting, OSM-only land, certified origin corridors, arrival, HTTP request bounds, and privacy of access logs. An integration test uses the released coastline package and the real isolated worker protocol.
