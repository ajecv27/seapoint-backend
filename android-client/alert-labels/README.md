# Short alert labels and cached refresh

This native client update changes `lib/official_alert_feed.dart` and four
precisely matched blocks in `lib/main.dart`.

| Empty state | Label |
| --- | --- |
| Ready | No alerts |
| Verifying | Checking alerts… |
| Cached or source cache | No alerts reported · saved |
| All pages fetched, with historical bulletins | No alerts reported |
| Partial check failure | Unable to confirm alerts |
| Unavailable | Unable to check alerts |
| Unknown | Alert status unavailable |

Active warning names and their verification, saved, stale, and partial-check
qualifications stay unchanged. Full source diagnostics remain available by
long-pressing the synopsis.

Restored cached reports now trigger a fresh startup check even when the saved
check was recent. Existing retry backoff remains in effect. A slow cache read
cannot replace a live report received meanwhile. The two initial checking
messages also use “Checking alerts…”.

The Windows PowerShell 5.1-compatible installer accepts all four previous
helper versions. It validates each main block as either its unique old or
unique updated form, allowing partially applied updates and preserving arbitrary
unrelated code. It preserves every unpatched byte, existing line endings and
UTF-8 BOM, including mixed line endings. It stages both results, verifies the
helper download and checks for concurrent edits before installation.

Both exact originals are backed up under `.seapoint-backups/alert-labels-*`
before either file is written. A failed write or installed-byte verification
restores both originals; restoration of the second file is still attempted if
restoration of the first fails. A repeated, fully installed update changes no
files and creates no backup. Unrecognized helper changes and missing or
ambiguous main blocks are refused before downloads or project writes.

Run the installer from the SeaPoint project folder in the Android Studio
Terminal, then run `flutter analyze` and click **Run** in Android Studio.

This delivery directory contains the intended installer, helper, tests and small
main patch manifest; it does not publish them. Full `main.dart` is a private
fixture under `baseline/`, outside the public `android-client/` paths.
`test_installer.py` uses disposable local projects and local downloads. Its
21 fixture groups run under the available PowerShell runtime; Windows
PowerShell 5.1 compatibility is maintained in the installer syntax.
