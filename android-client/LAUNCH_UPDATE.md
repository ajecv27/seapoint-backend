# SeaPoint launch update

Run `launch-update.ps1` from the Flutter project folder in Android Studio's
PowerShell terminal. The updater validates all target blocks first, backs up
`lib/main.dart` and the Android manifest under `.seapoint-backups`, then applies
only the required changes. Rerunning an installed update leaves files untouched.

This includes the earlier lazy Navigation initialization, starts cache loading
and weather refreshes after the dashboard's first frame, and adds a radar UI
version query so the WebView requests the updated rain player. The main Android
manifest receives the Internet permission if it is missing, so release builds
can use the existing online weather and radar services. Existing location
permissions, source edits, and formatting remain intact.

After installation, run `flutter analyze`. Stop any current Android Studio debug
session, connect the phone, and run `flutter run --release`. The first compile and
installation can take time; assess app startup afterward by closing the app and
opening it from the phone's icon. This is a local development installation using
the project's existing signing configuration, not a store release.

The first-frame check proves the dashboard renders while its preferences read
is pending and that Navigation has not initialized. It does not establish the
cause of a particular phone's reported 30-second Android splash. If that delay
persists in the installed release build, capture a phone startup trace using
`flutter run --profile --trace-startup` for further diagnosis.
