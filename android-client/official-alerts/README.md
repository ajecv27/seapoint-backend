# Official alerts and synopsis in one card

One **Official Weather** card lists current supported **Alerts**, followed by the
short, complete official **Synopsis**. Supported categories include small-craft
advisories/warnings, high-surf advisories/warnings, tropical-storm and hurricane
watches/warnings, and local flood products. Island names distinguish Antigua
and Barbuda where their notices differ. The backend verifies the official
products; an unreadable, unavailable or stale source is unverified coverage,
never an all-clear. The card appears above the daily forecast list and does not
invent warnings for future days.

Each named alert opens its validated official bulletin link. Multiple alerts
keep the selection dialog. The synopsis uses the official airmass discussion,
with complete text and qualifiers, rather than replacing it with the Tonight
forecast. Full source and verification details remain available.

Structured HTTP200/503 reports preserve coverage diagnostics and source links.
Cached alerts are marked unverified and retain their original observation and
expiry clocks. Verified cancellation/source changes clear old names. Expired
names are pruned on the existing minute/resume refresh, not held until a later
poll. Legacy responses cannot establish an all-clear.

## Install

Run `android-client/official-alerts-update.ps1` from the Flutter project root,
then `flutter analyze` and Android Studio Run. It supports the preceding
weather/navigation polish or combined-card versions. The installer verifies all
source/payload hashes, creates backups under `.seapoint-backups/`, and restores
files on write failure. It updates main.dart, the synopsis helper, the card
widget and the new alert-feed model. Navigation, GPS permissions, dependencies
and trip calculations are preserved. Existing releases remain unchanged.

Client regression checks cover503/legacy/partial responses, cancellation/source
changes, bounded cache retention, expiry, safe official links, complete synopsis
text and the combined card. Both supported installer baselines and repeat/repair,
corruption, source-refusal and rollback cases are tested. Expanded official
source support also requires the corresponding deployed backend update.
