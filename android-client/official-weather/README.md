# Combined official weather card

The Weather dashboard now shows the warning status and concise official island
outlook together in one card with one action. The existing warning and bulletin
opening behavior is retained: a current warning can open its associated document;
otherwise the existing bulletin selection/source is used.

## Install

Run `android-client/official-weather-update.ps1` from the SeaPoint Flutter project
folder in the Android Studio Terminal. Then run `flutter analyze` and click Run
in Android Studio to load the update on the connected phone.

This installer requires the previous weather/navigation polish version of
`lib/main.dart` and its existing `weather_synopsis.dart` helper. It validates
those versions before downloads or writes and stops if it finds custom changes.
It verifies downloaded payloads, backs up the original main file under
`.seapoint-backups/`, and restores original bytes if writing fails. Re-running
an installed update is safe.

Only `lib/main.dart` and the new `lib/official_weather_card.dart` are written.
Navigation, trip recording, the existing synopsis helper, dependencies and
Android permissions remain unchanged. The patch contains the changes to the
existing screen rather than a copy of the full app.

## Checks

Five card widget tests passed. Eleven PowerShell fixture groups passed, including
CRLF/BOM inputs, repeat installation, refusal of custom files, corrupt downloads,
partial installation repair and exact-byte rollback after either write.
A real phone check is still needed for the final installed app appearance.
