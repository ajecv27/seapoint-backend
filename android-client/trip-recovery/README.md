# SeaPoint trip recovery

The Android update saves the active route and accepted GPS measurements in the
app's private support directory. Each appended record is flushed to disk. Start
records use a same-directory staging file and rename; writes are serialized so
slower storage cannot put a GPS point after a stop or into a different trip.

When Navigation opens, an unfinished trip offers Continue, Finish saved trip, or
Discard. Continue retains the original start time, so elapsed time and overall
average include the interruption. It starts a separate measured track segment;
no connecting distance is invented for time with the app closed. Finish uses the
last saved clock, excluding the later interruption. The most recent completed
trip remains available alongside a new active trip. This is not a trip-history
archive. Recovery never claims to reconstruct GPS measurements that were not
saved.

A truncated or corrupt journal recovers only its complete valid prefix. Invalid
later measurements cannot inflate its saved time, distance, or maximum speed.
Storage failures display a visible saving warning instead of silently claiming
success. A journal has a 64 MiB limit. Parsing/replay runs in a background isolate
on Android to avoid blocking the map while restoring a longer recording.

## Installation

Use the pinned `trip-recovery-update.ps1` command supplied in the chat from the
Android Studio PowerShell terminal in the folder containing `pubspec.yaml`.
Then run `flutter pub get`, `flutter analyze`, and `flutter run --release`.

The self-contained installer preflights all 19 source/dependency patches and
verifies new embedded helpers before writing. It preserves unrelated edits,
line endings, BOMs, existing dependency declarations and Android permissions.
It backs up originals under `.seapoint-backups/trip-recovery-*`, supports safe
reruns, and rolls back partial writes. The published patch contains targeted
deltas and new helpers, not the complete private application source.

## Existing routing service

The handoff describes a separate local FastAPI/Docker routing service. Its
source and coastline data are absent from the supplied ZIP and connected
repository. The upload's `backend/server.py` is a weather/alerts server, not the
route calculator. Its land-avoidance algorithm must be located and reviewed
before deployment; route generation has not been replaced with straight lines.

The installer also adds and runs `tool/find-routing-service.ps1`. It reads Docker
container names/ports, bind-mount paths and the Compose project-folder label to
help locate that project. It reads no environment variables, credentials or
source contents, changes no containers and uploads nothing. Open Docker Desktop
and rerun that checker if Docker is unavailable. Share its routing-check output
in the chat to identify the original project. Phone users still need the
existing routing service until its production deployment is completed.

## OpenWeather

Current app weather/marine requests use Open-Meteo; observed radar uses
RainViewer; forecast maps use NOAA GFS and Meteo-France AROME. Official bulletins
use Antigua and Barbuda Meteorological Services; tides use WorldTides. Current
app/player code makes no OpenWeather One Call requests. That subscription is
not required for these current features. Account subscriptions were not changed.

## Validation

- Flutter analysis: no issues; all 110 Flutter tests passed.
- Tests cover real-file restart recovery, interrupted writes, preserved
  completed trips, serialized writes, visible recovery choices, storage failure,
  corrupted-prefix recovery, nautical statistics and unrecorded GPS gaps.
- PowerShell fixture checks cover Windows BOM/CRLF, backups, reruns, preserved
  edits/dependencies, conflicting files, verified payloads and write rollback.
- Routing-check process tests preserve Docker formatting arguments and handle
  an unavailable Docker daemon without failing the trip update.

Live GPS, actual Android process-kill recovery and screen-lock behavior still
need checking on the phone. Keep Navigation open while recording during these
checks; this update does not add an Android background location service.
