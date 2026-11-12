# SeaPoint weather and navigation display update

The Weather outlook card now shows a short, complete forecast from the official
bulletin, with its period label and rain probability. The formatter uses the
provided Today forecast when present, otherwise Tonight or Tomorrow. For example:
`Tonight: Partly cloudy with a 40% chance of showers.` The full official synopsis,
all forecast periods and verification information remain in the tooltip and
cached source. A tap opens the official bulletin. The text wraps as needed
instead of ending with an ellipsis. Cached synopsis-only text is also supported;
unknown qualifiers are preserved rather than guessed or discarded.

The radar entry now says only `Rain Radar` and opens the existing radar screen.

The navigation position marker is a blue circle before or after a trip. During
an active trip it becomes a blue arrow pointing along the phone compass, matching
the existing compass display. Rotating the phone updates it without needing GPS
movement. Map rotation is handled by the native map. If the compass or arrow
asset is unavailable, the circle remains. Compass-driven map updates are
coalesced and capped at 20 per second. GPS course statistics and the black GPS
trail remain independent of phone orientation.

## Install

Run `android-client/weather-navigation-update.ps1` from the Flutter project root.
This update requires the navigation trip-recording update and accepts the
original or compact Weather dashboard. The installer validates both screens and
helper versions before writing, verifies downloaded payload hashes, creates
backups under `.seapoint-backups/`, and restores files after a failed write.
Re-running is safe. It preserves the local manifest, trip recorder and trip
statistics widgets. No backend deployment is needed.

After installation, run `flutter analyze`, then use Android Studio Run to load
the app on the connected phone. Rotate the phone after starting a trip to check
the native arrow; stopping the trip restores the circle.

## Validation

The app was checked with Flutter 3.47.8 / Dart 3.13.7 and its existing packages.
Full app analysis reports no issues. All 53 Dart/widget tests and 14 PowerShell
installer fixture groups passed. Tests include complete forecast periods, probabilities, negations, time/place
qualifiers, abbreviations and grammar, plus active/idle marker state and heading
normalization. Existing recorder and trip-widget checks remain included. Pure
Dart and widget tests run in the minimal Flutter harness used for this project,
which avoids an unrelated native-hook analytics write in this cloud environment.
Actual Android compass calibration and native map rendering require a phone check.
