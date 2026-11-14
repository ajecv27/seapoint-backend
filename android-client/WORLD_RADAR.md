# Worldwide rain forecast update

The published radar now supplies 48-hour forecasts around the world, with finer
regional data retained around the eastern Caribbean. Observed radar still uses
RainViewer and depends on available radar feeds. Global maps cover normal Web
Mercator latitudes (approximately 85°S–85°N).

Run `world-radar-update.ps1` from the Flutter project folder in Android Studio's
PowerShell terminal. It first verifies live worldwide coverage, then requests
the new page version in the app. Earlier lazy Navigation and first-frame startup
changes are included for projects that have not installed them. It adds Internet
permission to the main Android manifest if missing for release builds, preserves
existing source edits and permissions, creates backups under `.seapoint-backups`,
and can be rerun safely.

Run `flutter analyze`, stop the current debug session, and use
`flutter run --release` with the phone connected to install the updated app.
The first compilation/install can take time; measure startup afterward by
opening SeaPoint from its phone icon.
