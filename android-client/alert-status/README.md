# Clear Met Office alert status

When no current alert is confirmed and some official checks are stale, the card
now explains: “No current alerts confirmed; some Met Office bulletins are out of
date.” Failed checks and wholly unavailable reports have distinct messages.
Confirmed active names remain fully visible. Cached reports stay unverified.

Source details use readable Marine, Tropical cyclone and Flood summaries,
counting checks rather than URLs, with stale issued months in Antigua time.
This is a presentation update: parsing, verification, cache lifetimes, retention,
HTTP handling and serialized metadata are unchanged. It does not turn incomplete
coverage into an all-clear or substitute another provider for Antigua Met.

Run `android-client/alert-status-update.ps1` from the Flutter project root, then
`flutter analyze` and Android Studio Run. Only official_alert_feed.dart is
changed. The installer checks the previous version and downloaded hash, creates
an exact backup and rolls back after failed verification. Reruns are safe.
Other app files and saved app data are untouched.
