# Compact alert wording

When every Met Office page can be fetched but some still contain only historical
bulletins, the card now says “No alerts reported” instead of the long out-of-date
bulletins explanation. A fresh, fully verified empty report still says “No alerts”.
Named warnings, failed checks, cached status, and detailed source diagnostics keep
their existing meanings. The source details remain available by long-pressing
the synopsis.

This native client update changes only lib/official_alert_feed.dart. It accepts
all three earlier official-alert helper versions, verifies the download, preserves
an exact backup, and restores it if verification fails. Reruns are safe. Run
flutter analyze and Android Studio Run after installation.
