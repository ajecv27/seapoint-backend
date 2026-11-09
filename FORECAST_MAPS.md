# Radar and 48-hour forecast playback

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

The forecast is prepared in a background thread on the first request. During
preparation `/forecast-frames` returns HTTP 202; the player keeps radar available
and checks again after 15 seconds. The first build downloads/decompresses 50
precipitation records and can take longer on a small Render instance. Frames are
reused from disk, and failed updates back off for five minutes. A prior forecast
is retained only while its model run is less than 24 hours old.

`SEAPOINT_FORECAST_CACHE` optionally sets a writable cache directory; the default
is `forecast-cache/` beside the module. Ephemeral storage works, but restarts or
new instances may regenerate images. Processing and outbound data still consume
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

The backend returns an hourly image bracketing the exact `forecast_until` time
(now plus 48 hours), and the slider ends at that timestamp. Fifty cached hourly
images support this horizon. Extensions reuse images and fetch only new records.
The existing Android WebView loads this change without another app rebuild.
