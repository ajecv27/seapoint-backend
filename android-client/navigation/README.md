# SeaPoint navigation trip recording

Starting a planned route now records measured GPS travel behind a boat marker.
The planned route stays cyan; the accepted GPS trail appears black with a white
casing. The trail follows actual positions, including deviations from the plan.
The boat points along GPS course over ground, independently of the phone compass
and map rotation.

The live panel shows current, maximum and overall average speed (knots), GPS
heading, recorded distance (nautical miles), and elapsed time. Stop Trip opens a
summary of average/max speed, distance and time. The last summary can be reopened
while the navigation screen remains open. New Route and leaving an active trip
present its summary before clearing/leaving. Reaching a waypoint does not silently
stop recording.

## Install in the Android Studio project

Run `android-client/navigation-trip-update.ps1` from the Flutter project root,
then run `flutter analyze` and use Android Studio Run to install the app.
The installer validates the uploaded navigation source version, downloads
SHA-256-verified additions, and backs up changed files under
`.seapoint-backups/`. It stops before writes if the local navigation source or
existing helper files differ. It preserves the local Android manifest and adds
only missing foreground location and network permissions. Re-running is safe.
The patch contains changes to the uploaded navigation file rather than a copy of
the complete existing app source. No backend deployment is needed.

## Recording details

- 1 nautical mile = 1,852 metres; knots = metres/second × 3,600 / 1,852.
- Average is recorded distance divided by the whole elapsed trip, including stops.
- Poor, stale, invalid, out-of-order and implausible fixes cannot inflate the trail.
- GPS gaps longer than 30 seconds start separate line segments. Unmeasured gap
  distance is excluded, and the summary reports gaps.
- Current speed and GPS heading become unavailable after 10 seconds without a
  reliable measurement. Stationary GPS course is unavailable; the boat retains
  its last measured orientation. The magnetic compass remains a separate display.
- This version records while the navigation screen is running. It does not add
  background location, saved trip history or process-restart recovery.

## Validation

Full uploaded Flutter app with the new integration: `flutter analyze` passed
with no issues, using Flutter 3.47.8 / Dart 3.13.7 and the existing dependencies.
Twenty recorder tests, three map-data tests and five widget tests passed.
Widget checks include 320px width and 2× text scaling.
Ten PowerShell installer scenario groups passed, including mismatched source,
corrupt downloads, repeat installs, manifest preservation and rollback. Tests ran in a minimal
Flutter test harness to avoid an unrelated `objective_c` native-hook analytics
write to a read-only home directory in this cloud environment.

The tests in `tests/` import `package:seapoint/...`; copy them into a SeaPoint
project's `test/` folder to run with `flutter test`. Real Android GPS movement,
permissions and native MapLibre rendering still need a phone check.
