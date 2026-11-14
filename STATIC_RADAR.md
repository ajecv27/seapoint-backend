# Published radar without Render startup waits

`static_site/export.py` builds the existing radar player and a complete, verified
forecast into a static GitHub Pages artifact. Phones load this published site
directly. Model downloads and rendering run in GitHub Actions each hour, without
waiting for a phone to open the radar or for the Render service to wake.

The existing weather dashboard, alerts and tides keep their current providers.
This change removes Render from the radar page and its forecast image requests;
it does not move all weather endpoints or change rain motion rendering.

## Enable the site once

1. Open repository **Settings > Pages** and set **Source: GitHub Actions**.
2. Open **Actions > Publish radar > Run workflow** on `main`.
3. Wait for the deployment to succeed. The site is
   `https://ajecv27.github.io/seapoint-backend/` and its readiness document is
   `https://ajecv27.github.io/seapoint-backend/health.json`.
4. Run `android-client/static-radar-update.ps1` from the Flutter project folder.
   It checks the actual published site before changing `lib/main.dart`, backs up
   the original outside `lib`, preserves local edits and supports reruns.
   Run `flutter analyze`, stop the app, and Run it again in Android Studio.

GitHub's standard workflow token can deploy Pages after the repository setting
is enabled; it cannot enable Pages itself. No API keys or new subscriptions are
needed. The first workflow will fail at Configure Pages until that setting is
turned on. Scheduled Actions may be delayed by GitHub, so this is not a guarantee
of hourly publication. GitHub may disable scheduled workflows after repository
inactivity; monitor Actions and re-enable the workflow if needed.

## Publication and freshness

The build prepares 54 hours of hourly frames to leave a six-hour buffer around
the rolling 48-hour display. Each manifest keeps source/model issue times, fetch
times, per-provider bounds and precipitation period semantics. The build does
not label an old forecast as newly issued. AROME supplies regional detail where
available; GFS supplies remaining hours. Sources are not morphed across models.

Every PNG is decoded and checked before the manifest switches. A failed build
does not deploy, so Pages retains the last successful artifact. Immutable image
URLs include a content digest, and prior generations remain for 24 hours for
already-open pages. Cached public model downloads are reused between builds.
Generated weather and binary assets are not committed to Git history.

The page reads observed radar metadata directly from RainViewer. Leaflet,
MapLibre and the integration plugin are pinned, integrity-checked at build time,
and served with the static page. Their licences are included. Basemap tiles,
fonts and terrain still use their public providers, with existing attribution.
All paths support the repository's `/seapoint-backend/` subdirectory.

The map information panel shows publication and model times, and marks a
publication delayed after three hours. A publication older than 24 hours is
rejected. Source model runs also expire at 24 hours. If updates stop, the UI uses
only valid remaining forecast coverage and does not invent a new 48-hour end.

## Local validation

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
python static_site/export.py --output _site --cache .radar-cache
SEAPOINT_STATIC_SITE="$PWD/_site" python tests/browser_static_site.py
```

The browser check requires Playwright and Chromium. It serves the actual built
site at a repository subpath, uses real generated model PNGs, blocks Render,
isolates external tile/observed feeds, verifies the buffered 48-hour timeline,
checks pan/zoom during playback, and rejects stale publications. It does not
measure weather accuracy or mobile network latency.

## Worldwide forecast coverage

The published player now combines a global NOAA GFS tile field with the existing
regional forecast PNGs. Global Web Mercator coverage spans 85.05°S–85.05°N and
all longitudes. The static builder prepares hourly global XYZ tiles at zooms
0–4 for the same 54-hour buffer; the app shows a rolling 48 hours. The original
0.25-degree GFS grid is sampled for display, without adding forecast resolution.
The same validated GRIB record is reused by regional and global renders.

Global tiles use immutable model-run/hour/style paths. Each frame's completion
record pins every tile checksum, and all PNGs are decoded before reuse. A failed
build retains the last deployed site. Source timestamps and precipitation-period
semantics remain attached to every frame. Global model runs expire after 24
hours in the player; their static assets remain for 25 hours from model issue.
Regional generation retention remains 24 hours from publication.

The phone downloads only the native tiles needed for its current viewport, nearby motion context and
nearby animation frames. It composes those tiles with the finer regional PNG in
a viewport-sized canvas, clearing the global rain beneath that region first.
This avoids drawing rain twice, and preserves genuinely dry regional pixels.
The client retains at most four completed viewport canvases and bounded image
caches. Panning/zooming does not pause playback; playback can buffer while new
area data loads, and a missing tile is shown as unavailable rather than dry.
Motion fields are computed for the current view and invalidated when it changes.

`tests/browser_global_forecast.py` uses explicit test-only global rain and a dry
regional field to check regional replacement, New York/London/Sydney/Cape Town,
longitude wrapping, pan playback, bounded caches and missing-tile recovery.
`tests/test_global_forecast.py` checks projection against source grid positions,
record integrity, tile reuse/rebuild, publication identity and source expiry.
`tests/global_rain_test.js` checks client projection and viewport geometry.

`android-client/world-radar-update.ps1` requests the updated page version after
checking that the live site advertises full worldwide coverage. It also includes
the earlier first-frame/lazy Navigation updates and release Internet permission,
with the same backup, validation and safe-rerun behavior as the launch updater.

At tight zoom levels, viewport canvases include enough surrounding geography for
the motion worker to track realistic hourly travel. The view context is clipped
to Web Mercator's latitude limits, so a zoomed-out world is not vertically
compressed by off-map pixels. The translated-cell regression checks forward
motion through all interpolation fractions at the initial close zoom.
