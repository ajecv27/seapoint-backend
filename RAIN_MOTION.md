# Rain-frame motion display

Adjacent rain images now use matched local pattern motion instead of a full-
interval dissolve of stationary images. The source weather fields, timestamps,
forecast horizon and observed radar remain unchanged.

A bounded browser worker estimates forward and reverse motion on a small image
pyramid. Correlation, reverse consistency and neighboring vectors reject weak
matches. Verified matches seed one field at the interval's midpoint. Connected wet
regions with multiple trusted matches receive spatially regularized motion;
regions without those anchors retain zero movement. Dry margins are extended
only for inverse sampling. This is display interpolation, not independent
tracking of every cell. Missing reverse coverage is distinguished from a
confident contradictory match.

A WebGL canvas warps the original-resolution images with that common field.
Colours are premultiplied before bilinear sampling, preventing dark cuts around
transparent rain edges. The original source endpoints remain pixel-exact.
The renderer uses one advected image pair instead of mixing moving rain with
a second stationary copy at confidence boundaries, removing a source of ghost
outlines. Uncertain regions do not borrow a global wind direction.
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
fails. Motion estimates add no observations or forecast resolution: AROME Antilles uses an approximately2.5km grid; its hourly fields are mean
rain rates. GFS remains the approximately28km fallback and longer-range tail. This is a display transition,
not a prediction of an individual rain cell's exact path.

Memory is bounded to four cached image-pair motion results, 24 readable tile
captures and one GPU image pair. The shared midpoint field is computed and
cached in the worker alongside the directional estimates. The next pair is
prepared in advance without changing the active GPU textures. On a cache miss,
playback holds at the source timestamp while the worker prepares motion, then
resumes without skipping forward. The server adds no processing library.

## Forecast contours

Forecast images use bounded cubic spatial sampling of the providers' rates.
Regional AROME rates come from differences of validated hourly accumulations;
GFS rates are instantaneous. Values stay within the four surrounding model values, with no new
extrema or wet cells in dry areas. Light-rain opacity rises continuously from
0 at 0.1 mm/hour to 200 at 0.6; stronger rates retain the existing colours and
opacity. This removes hard cyan outlines and coarse display corners without
increasing the model resolution. Versioned image names and a private cache
manifest prevent old-style images being reused after deployment. Old image URLs
remain readable for already-playing clients.

Both models still change precipitation shape and intensity between hourly
outputs. Those changes cannot establish the physical track of an individual
rain cloud; source handoffs remain distinct from interpolated same-source rain.

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

Pixel regressions also verify independent cells moving in opposite directions,
verified movement with one missing directional confidence field, rejection of
confident contradictory vectors, and common-field transfer from the worker.

## Motion-pair handover

During active playback, an unfinished motion pair retains the current GPU pixels
and source-layer opacities while the animation clock buffers. It does not replace
the current presentation with the new pair's earlier source frame. Once the pair
is ready, the renderer presents its selected time normally. Scrubbing, map moves,
failed motion preparation and unsupported GPU fallback retain their existing
behavior. This fixes a display handover; it does not change source rain data or
force genuine forecast changes to travel in one direction.

`tests/browser_rain_handover.py` deliberately delays preparation at an hourly
boundary. It checks that the displayed pixels and layer opacities remain intact,
that playback remains selected, and that the translated rain advances after the
worker resumes. The same case fails against the prior player because the visible
canvas is hidden. Set `SEAPOINT_STATIC_SITE` to a built static site to reuse its
pinned map libraries, or let the test retrieve the normal public library URLs.
