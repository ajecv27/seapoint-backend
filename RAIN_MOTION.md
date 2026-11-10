# Rain-frame motion display

Adjacent rain images now use matched local pattern motion instead of a full-
interval dissolve of stationary images. The source weather frames, timestamps,
forecast horizon and data providers are unchanged.

A bounded browser worker estimates forward and reverse motion on a small image
pyramid. Correlation, reverse consistency and neighboring vectors reject weak
matches. A WebGL canvas warps the original-resolution images and combines their
RGBA values without the old stacked-opacity dip. Source endpoints remain exact.
Appearance/disappearance, unreliable matches, missing WebGL or unreadable cross-
origin pixels use the nearest original rain frame instead of inventing movement.

Only adjacent same-source images with normal observation/forecast spacing are
interpolated. Source handoffs and coverage gaps do not receive synthetic rain.
Pan/zoom keeps playback running; observed capture is rebuilt for the new view.
RainViewer display tiles remain usable if a separate CORS-safe pixel capture
fails. Motion estimates add no observations or forecast resolution: GFS remains
an hourly model with an approximately28km grid. This is a display transition,
not a prediction of an individual rain cell's exact path.

Memory is bounded to four motion fields,24 readable tile captures and one GPU
image pair. Preparation runs in a worker; the server adds no processing library.

## Checks

- `node tests/rain_motion_test.js`
- `PYTHONPATH=/path/to/dependencies python -m unittest discover -s tests -p 'test_*.py'`
- Run the backend, then `SEAPOINT_TEST_URL=http://127.0.0.1:8766 python tests/browser_motion.py`
- Existing unified-timeline browser regression also passes.

Browser tests inspect output pixels for a single translating rain feature,
unchanged endpoints and stationary brightness. They check bounded caching,
actual cached GFS images, paused scrubbing, pan/zoom, source boundaries, data gaps
and unsupported/CORS-denied fallbacks. Cloud-browser timings are not phone
hardware measurements. Native Android WebView still needs a device check.
