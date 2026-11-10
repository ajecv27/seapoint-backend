# Rain-frame motion display

Adjacent rain images now use matched local pattern motion instead of a full-
interval dissolve of stationary images. The source weather frames, timestamps,
forecast horizon and data providers are unchanged.

A bounded browser worker estimates forward and reverse motion on a small image
pyramid. Correlation, reverse consistency and neighboring vectors reject weak
matches. A WebGL canvas warps the original-resolution images and combines their
RGBA values without the old stacked-opacity dip. Source endpoints remain exact.
Neighboring vectors are regularized, and inverse-warp and forward/reverse
consistency checks suppress folded or mismatched patches that created seams.
Unmatched rain grows or dissipates with a continuous premultiplied transition;
it no longer switches images halfway through the interval. Missing WebGL or
unreadable cross-origin pixels use an opacity-corrected image transition.

Forecast motion is calculated over the complete regional source image, with a
256-pixel working image and a 64-by-64 flow grid. Panning and zooming change its
placement, not the computed rain field. Observed radar uses readable tiles over
the visible map. Neither path is limited to the area around Antigua.

Only adjacent same-source images with normal observation/forecast spacing are
interpolated. Source handoffs and coverage gaps do not receive synthetic rain.
Pan/zoom keeps playback running; observed capture is rebuilt for the new view.
New radar tiles finish loading before that capture, and late tile loads can
recover immediately after a timeout instead of leaving movement disabled.
RainViewer display tiles remain usable if a separate CORS-safe pixel capture
fails. Motion estimates add no observations or forecast resolution: GFS remains
an hourly model with an approximately28km grid. This is a display transition,
not a prediction of an individual rain cell's exact path.

Memory is bounded to four motion fields, 24 readable tile captures and one GPU
image pair. The next pair is prepared in advance without changing the active
GPU textures. On a cache miss, playback holds at the source timestamp while the
worker prepares motion, then resumes without skipping forward. Preparation runs
in a worker; the server adds no processing library.

## Checks

- `node tests/rain_motion_test.js`
- `PYTHONPATH=/path/to/dependencies python -m unittest discover -s tests -p 'test_*.py'`
- Run the backend, then `SEAPOINT_TEST_URL=http://127.0.0.1:8766 python tests/browser_motion.py`
- Run `SEAPOINT_TEST_URL=http://127.0.0.1:8766 python tests/browser_smooth_flow.py`
- Existing unified-timeline browser regression also passes.

Browser tests inspect output pixels for a single translating rain feature,
unchanged endpoints and stationary brightness. They check bounded caching,
actual cached GFS images, paused scrubbing, pan/zoom, source boundaries, data gaps
and unsupported/CORS-denied fallbacks. The smooth-flow regression uses an actual
GFS image pair that exposed the midpoint jump, checks continuity separately from
a static fade, tests the full field at several map positions and zoom levels,
and forces slow preparation across two hourly boundaries. Cloud-browser timings
are not phone hardware measurements. Native Android WebView still needs a device
check.
