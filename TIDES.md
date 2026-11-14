# Tide request and credit control

SeaPoint requests one seven-calendar-day WorldTides `extremes` prediction for a
selected location. It does not request heights, plots or extra datums. Attribution
and all returned events are preserved. Times are grouped by the Antigua calendar;
no synthetic high/low events are inserted to make four changes per day.

## Phone cache

`tide_predictions.dart` reuses an installation's saved forecast while its original
coverage includes today through the seventh displayed day. Pull-to-refresh,
reopening the app, and switching back to a saved bay do not purchase that same
prediction again. A new calendar day may need a new prediction to fill the newly
displayed final day. Existing SharedPreferences tide entries migrate using their
original retrieval time; reading them never extends the prediction window.

A failed update keeps existing predictions for their original dates and shows
“Tide updates temporarily unavailable” where predictions are missing. Failures
and account pauses persist on the phone, preventing repeated network requests
when refreshing or switching locations. A deliberate pull-to-refresh can request
a controlled credit recheck (at most once per minute across the backend), so
adding credits does not require waiting the full automatic pause. A valid full
forecast is still reused during manual refresh. Nothing is presented as newly retrieved
merely because it was read from storage.

## Backend cache and limits

`X-SeaPoint-Tide-Client` is a random installation identifier retained on the phone.
It is not the provider API key. SQLite cache entries use its hash and normalized
coordinates; predictions are never shared between installations. Unidentified
legacy requests return 428 without calling WorldTides, so the guarded mobile
update is required. This follows WorldTides' mobile licence: predictions may be
stored and redisplayed to the same end user, not shared among mobile users.

Duplicate requests for the same installation/location coalesce. A fresh cache
entry is reused for the full requested calendar window. Provider calls serialize
so an exhausted-credit response pauses other locations immediately. Insufficient
credits or invalid credentials pause requests for six hours, including across
backend process restarts; transient errors back off the affected location for
15 minutes. The phone also saves the returned retry deadline.

`SEAPOINT_TIDE_DAILY_LIMIT` defaults to 50 upstream attempts per Antigua calendar
day for this development deployment. Cached predictions remain available after
the limit. Set an appropriate budget before a wider launch. This is an internal
guard, not a provider billing guarantee or multi-instance shared quota.

`SEAPOINT_TIDE_CACHE_DIR` defaults to `.tide-cache`. State files contain no API key;
directory/database permissions are private. On Render Free this disk is ephemeral
across deployments, so the phone cache is the durable copy. No paid database or
background keep-alive is introduced. Restarting alone does not clear a persisted
pause; a changed provider key starts a separate account-state namespace.

`GET /tides/status` reads local state without calling WorldTides. It reports the
service version, whether a key is configured, pause reason and retry time. The
API never returns or logs provider error bodies, API keys, installation tokens or
tidal-request coordinates. `GET /tides` retains its existing successful fields and
adds original coverage/fetch timestamps. Partial cached responses preserve those
timestamps and include the retry deadline.

Once credits are replenished, pull to refresh to request a controlled recheck,
or wait for the next scheduled check. A successful provider response clears the
account pause. The normal daily request cap still applies.
Existing predictions may remain visible while access is paused; adding credits
does not retrospectively fill dates that were never retrieved.

## Validation and licence references

Python tests use fake providers for same-day reuse, persistence, separate
installations, concurrent refreshes, exhausted-credit/credential responses, daily
limits, outages, full returned event lists and partial coverage. Flutter tests
cover phone restart, bay switching, old cache migration, calendar boundaries,
duplicate refreshes, invalid responses and persisted retry pauses. The updater
is tested under native Windows PowerShell 5.1 and PowerShell 7 with backups,
idempotence, unrelated edits and rollback.

WorldTides documentation: https://www.worldtides.info/apidocs

WorldTides caching/mobile licence: https://www.worldtides.info/terms

WorldTides attribution: https://www.worldtides.info/copyright

Tides remain supplemental weather information. They are not used to validate
navigation depth or vessel clearance.
