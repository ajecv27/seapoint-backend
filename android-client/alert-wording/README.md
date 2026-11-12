# Confirmed no-alert wording

When fresh Met Office checks are complete and report no active alerts, the
card now says exactly “No alerts”. Named active warnings and every cached,
incomplete or unavailable status keep their existing meaning.

This native client update changes only lib/official_alert_feed.dart. It
supports both earlier official-alert helper versions, verifies the download,
preserves an exact backup, and restores it if verification fails. Reruns are
safe. Run flutter analyze and Android Studio Run after installation.
