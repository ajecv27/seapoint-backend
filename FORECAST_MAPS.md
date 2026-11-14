# Radar and 48-hour forecast playback

## Regional rain detail

Météo-France AROME Antilles supplies hourly mean rain on an approximately2.5km
grid, replacing coarse GFS images where a valid regional image exists. Actual
public GRIB surface accumulations are differenced over consecutive same-run
hours and rendered in Web Mercator. This is forecast rainfall, not observed or
simulated radar reflectivity. The source is credited under Etalab Open Licence2.0.
No new API key or paid weather subscription is required.

AROME ends at48hours from its issue time. NOAA GFS supplies the final hours
required for a rolling48hours from now, missing regional hours, and fallback
coverage during regional outages. Each frame retains its own provider, model
issue time, geographic bounds and rainfall semantics. The info panel identifies
both sources; the existing map controls and single timeline stay in place.
Different models are never morphed together. A source handoff displays one
actual forecast image. Hourly interpolation adds no forecast detail or physical
rain-cell tracking.

A complete GFS horizon remains usable while the regional cache prepares; the
phone retries metadata every15seconds during that build and progressively
replaces only successfully loaded regional images. Missing images retain valid
loaded GFS coverage. Reported horizon/coverage uses actual available timestamps.
`arome-cache/` contains only selected precipitation GRIB records, PNGs and an
atomic manifest, with age/format checks and bounded downloads. It is ignored by
Git. A failed build preserves the previous valid cache and respects retry backoff.

Provider checks: `python -m unittest discover -s tests`.
Phone integration: `SEAPOINT_TEST_URL=http://127.0.0.1:8781 python tests/browser_regional_forecast.py`.


SeaPoint's existing `/radar` WebView now loads a player with observed RainViewer
radar, a NOAA GFS precipitation forecast, play/pause, a draggable time slider,
and smooth blending between hourly forecast images. No Android app replacement
is needed: the existing RadarScreen already loads this backend page.

The player is one Radar view with a continuous recent-observation-to-48-hour-forecast timeline. It opens on the latest observation; the first Play starts from the earliest recent radar frame and continues into predictions.
A green land / blue water vector map with subtle terrain shading has a compact intensity legend, floating map controls, and a dark bottom playback panel. Source details are available
through the info button. Observations and forecasts have explicit labels and
separate legends. Radar playback advances a ten-minute image interval over two
seconds, then holds the latest observation for 2.5 seconds before continuing into
forecasts. Only the end of the 48-hour forecast loops back to the beginning. Interpolation smooths
images only; it is not additional weather data or a radar nowcast. RainViewer
coverage can be incomplete. Missing images are never described as dry weather.

## Forecast data

- Public NOAA GFS 0.25-degree instantaneous surface precipitation rate (PRATE).
- Hourly frames covering approximately the next 48 hours; actual times appear
  at both ends of the slider. Model runs update six-hourly with publication time
  allowed. Units are converted from kg/m²/s to mm/hour by multiplying by 3600.
- Regional overlay: 10–23°N, 68–55°W, covering Antigua/Barbuda and the eastern
  Caribbean. Grid spacing is approximately 28 km, which limits island-scale
  detail. Smoothing does not increase forecast resolution.
- The selected GRIB record is fetched using HTTP byte ranges, validated, cropped
  to the region, and projected to Web Mercator for alignment with the map.
- Precipitation below 0.1 mm/hour is transparent. Higher intensities use the
  labelled forecast scale. Provider observations retain RainViewer's colours.
- Basemap/place labels: OpenFreeMap, OpenMapTiles, and OpenStreetMap. Terrain shading: Esri, USGS, NOAA. Existing basemap/provider terms and attribution
  requirements still apply; this is a development implementation, not a review
  of commercial data licensing.

## Render

Keep the current `python cloud_server.py` start command and install the updated
`requirements.txt`. ecCodes' Python distribution supplies its decoder library
on supported Linux platforms. The added dependencies are NumPy, Pillow, and
ecCodes; no NOAA or OpenWeather key is needed for the forecast maps.

The server starts preparing the forecast in a background thread at startup,
without waiting for the first radar request or delaying HTTP startup. During
preparation `/forecast-frames` returns HTTP 202; the player keeps radar available
and checks again after 15 seconds. The first build downloads/decompresses 50
precipitation records and can take longer on a small Render instance. Frames are
reused from disk, and failed updates back off for five minutes. A prior forecast
is retained only while its model run is less than 24 hours old. The returned
`forecast_until` is capped at the last available image; `coverage_complete` says
whether the full requested 48-hour horizon is currently covered.

After a successful full build, the server atomically saves `manifest.json` before
publishing the new forecast in memory. A restart can immediately serve a valid
local manifest while refreshing or extending coverage in the background. Restore
checks bound manifest size and frame count, validate NOAA metadata, model-run and
hourly timestamps, require matching local image URLs, and verify every PNG.
Expired, malformed, missing, corrupt, oversized, or symlinked cache entries are
ignored. Failed manifest publication retains the previous disk and memory copies.

`SEAPOINT_FORECAST_CACHE` optionally sets a writable cache directory; the default
is `forecast-cache/` beside the module. Cache reuse requires the same filesystem;
an ephemeral filesystem reset or a new instance still regenerates images.
An idle-host wake-up may also delay the initial response; the hosting plan and
its sleep behavior have not been verified here. Processing and outbound data still consume
hosting resources even though the data requires no subscription. Two-day-old
images are cleaned up. The endpoints are:

- `/forecast-frames`: status, model run, source, bounds, and timestamped image URLs.
- `/forecast-frame/YYYYMMDDHH-FFF.png`: immutable cached forecast image.
- `/radar`: embedded map player (existing Flutter URL).

The OpenWeather current-conditions endpoint from the initial draft has been
removed from this proposal. Open-Meteo weather/marine forecasts, official alerts,
tides, routing, and the Android layout are unchanged.

## Checks

```sh
python -m unittest discover -s tests -v
```

Unit tests use synthetic fixtures, clearly isolated from production data.
Browser integration has also been exercised locally with actual NOAA frames,
including play/pause, future-time scrubbing, mobile layout and provider failure
behavior. Render deployment and Samsung WebView performance still need testing.

With Playwright and Chromium installed in your development environment, run
`SEAPOINT_TEST_URL=http://127.0.0.1:8000 python tests/browser_radar.py` against a
running local backend. `CHROMIUM_PATH` overrides the browser executable, and
`RADAR_SCREENSHOT` optionally saves a preview. External assets are fetched with
Python's TLS-verifying HTTP client so managed proxy CA trust also works in the
browser test. Provider outages in these tests are deliberate test-only mocks.

## Basemap rendering

`/basemap-style` caches OpenFreeMap's Liberty style and applies SeaPoint's map
colours. Satellite imagery, 3D buildings, and street-map clutter are removed.
Actual coastline geometry and place names are retained. MapLibre renders the
vector map inside the existing Leaflet weather player; Esri's grayscale
hillshade is blended lightly over it to retain gentle terrain relief. No
additional subscription or API key is required.

The browser needs WebGL (available on the target Samsung device). The automated
browser checks allow Chromium's software WebGL renderer in the test environment.
Weather overlays remain independent of the basemap, and the source details
report a basemap loading failure rather than inventing geography.

## Compact controls and app title-bar info

The location pill and duplicate layer badge have been removed. The playback
panel sits 8px above the safe area. The bottom branding strip is replaced by
an accessible top info/credits button; required map attribution is presented
briefly on load and then remains available in that panel.

High-density screens request RainViewer's documented 512px tiles while retaining
256px logical tiles and native zoom 7. Provider smoothing remains enabled, and
a light blur on the radar layer softens block edges without blurring labels
or inventing additional weather detail.

To place the info icon in the native Android title bar, the small guarded
`android-client/add-header-info.ps1` patch updates only the existing radar
widget. It checks both expected insertion points before writing and creates a
backup. Rebuild/run the Flutter app afterward. The app title-bar icon calls the
same web info panel and hides its fallback web button. Until the app is rebuilt,
the top-of-map info button remains available.

## Unified past-to-future timeline

The selector is removed. Observation frames form the history; the previous-hour
GFS image is retained only for interpolation, never interleaved with observations.
The source label and intensity legend change when predictions begin. A Now marker
and the trailing Go to now action help return to current conditions. Observation
and prediction images are never crossfaded into one another; a source gap is
shown explicitly as unavailable rather than clear weather.

With complete coverage, the backend returns an hourly image bracketing the exact
`forecast_until` time (now plus 48 hours), and the slider ends at that timestamp.
If an update fails, the slider ends at the actual remaining coverage. Fifty cached hourly
images support this horizon. Extensions reuse images and fetch only new records.
The existing Android WebView loads this change without another app rebuild.

## Forecast recovery on the phone

The hosted page retries failed forecast metadata and missing images after
15 seconds, including network errors, unavailable responses and malformed JSON.
A request deadline prevents a stalled connection from blocking later attempts.
Returning to the app or reconnecting also refreshes the data on the same page.
Existing complete images remain usable during a failed update, within their
original model age and timestamps.

Observed radar becomes playable while forecast images download. Successfully
loaded forecast hours appear progressively; one missing image no longer removes
the entire forecast. The slider ends at the coverage actually loaded. Missing
intervals are identified as unavailable, and different model runs are not
interpolated into each other. Missing hours are retried even when the manifest
has not changed. The compact playback detail shows forecast preparation or
reconnection while only observations are available.

These changes run on the public backend page. Close and reopen Rain Radar on
the phone to load the updated page; a laptop connection is not required. The
phone still needs an internet connection to fetch new weather data.

`SEAPOINT_TEST_URL=http://127.0.0.1:8772 python tests/browser_forecast_recovery.py`
exercises isolated network failures, partial images, browser resume events,
retained forecasts and expiry during the observation-to-forecast handoff.

## Playback polish

Playback is 20% faster while keeping the observation and forecast pacing
distinct (360 and 2160 timeline seconds per real second). Panning, pinch zoom,
zoom buttons, and recentering leave playback running; manually scrubbing the
time slider or pressing pause still stops it. The info button has a smaller
34px visual circle and 18px icon with a 44px touch target. The Android header
patch also supports resizing an already installed native info action, with a
backup and guarded matching before changing the Dart file.

## Startup performance

The HTTP socket binds before numerical provider imports and cached-image
validation. A single background initializer restores/prepares the forecast;
metadata remains explicitly loading or unavailable until it is usable. Basic
HTTP routes and the radar shell do not wait for that initializer.

The radar page needs Leaflet for its basic map and controls. It notifies the
native app after the first UI frame; MapLibre, hillshade and motion processing
then load independently with bounded retries. Existing weather images remain
playable through the opacity-corrected fallback while optional scripts load.
The original map style, sources and48-hour timeline return as resources arrive.

The native startup patch delays Navigation/GPS creation until the Navigation tab
is first selected, then retains it for ongoing trips. Radar can recover a missed
ready message and presents Retry after a long wait without aborting a pending
page request. The guarded installer preserves exact backups of both Dart files.

Render Free sleeps after15minutes without incoming requests and may take about
a minute to wake: https://render.com/docs/free . These code changes remove
avoidable application work; they do not remove the hosting platform's idle wake.
The delayed-script browser benchmark uses an artificial10-second resource hold
and is not a phone hardware or Render cold-start timing guarantee.

## Global static delivery

The regional API remains available for existing clients. The GitHub Pages app
also publishes worldwide GFS tiles through `global_forecast.py` and combines
them with those regional images using `global_rain.js`. The detail in the
AROME Antilles footprint is preserved; outside it the actual GFS grid is about
28 km. Its global PRATE field is total precipitation in water-equivalent mm/h,
which can include frozen precipitation at colder locations. Only visible-area
tiles are downloaded on the phone. Full publication, freshness and client
memory behavior are documented in `STATIC_RADAR.md`.
