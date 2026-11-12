# SeaPoint startup update

Navigation's GPS, compass and native map now initialize when the Navigation tab
is opened for the first time. The tab remains mounted afterward, preserving
its route, trip recording and map state when switching back to Weather.

Radar can recover a missed JavaScript ready message after the map boots. A
30-second watchdog shows the existing Retry action if loading takes too long;
it does not cancel the pending page load. Successful loading still opens the map.
The compact native map-information button, when installed, is retained.

The Windows PowerShell 5.1-compatible installer changes only known startup
blocks in `lib/main.dart` and `lib/radar_screen.dart`. All patches are embedded;
it downloads no Dart payloads. It validates both files before writing, preserves
unrelated edits and original UTF-8 BOM/line endings, and saves exact backups of
both originals under `.seapoint-backups/startup-*`. If a write fails verification,
both original files are restored. A repeated install creates no new backup or
file changes. Missing or ambiguous patch blocks are refused before installation.

Run the update from the SeaPoint project folder in Android Studio's Terminal,
then run `flutter analyze`, stop the app and click Run to install it on the phone.
This update does not change the hosting plan; a hosting service waking from idle
may still delay the first network response.
