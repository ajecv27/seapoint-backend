import 'package:flutter/material.dart';

/// One official-weather entry with distinct warning and outlook information.
/// Status strings are shown in full, including cached/unverified qualifications.
class OfficialWeatherCard extends StatelessWidget {
  const OfficialWeatherCard({
    super.key,
    required this.warningStatus,
    required this.outlookText,
    required this.sourceDetails,
    required this.hasActiveWarnings,
    required this.onOpenBulletin,
  });

  final String warningStatus;
  final String outlookText;
  final String sourceDetails;
  final bool hasActiveWarnings;
  final VoidCallback onOpenBulletin;

  @override
  Widget build(BuildContext context) {
    const accent = Color(0xFF087D9D);
    final warningColor = hasActiveWarnings
        ? Theme.of(context).colorScheme.error
        : Theme.of(context).colorScheme.onSurface;
    return Card(
      child: InkWell(
        onTap: onOpenBulletin,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    hasActiveWarnings
                        ? Icons.warning_amber_rounded
                        : Icons.cloud_outlined,
                    size: 22,
                    color: hasActiveWarnings ? warningColor : accent,
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Official Weather',
                      style:
                          TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                  ),
                  const Icon(Icons.open_in_new, size: 18, color: accent),
                ],
              ),
              const SizedBox(height: 8),
              Text.rich(
                TextSpan(
                  children: [
                    const TextSpan(
                      text: 'Alerts: ',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    TextSpan(text: warningStatus),
                  ],
                ),
                style: TextStyle(
                  fontSize: 12,
                  height: 1.3,
                  color: warningColor,
                  fontWeight:
                      hasActiveWarnings ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
              const SizedBox(height: 5),
              Tooltip(
                message: sourceDetails,
                child: Text.rich(
                  TextSpan(
                    children: [
                      const TextSpan(
                        text: 'Synopsis: ',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      TextSpan(text: outlookText),
                    ],
                  ),
                  style: const TextStyle(fontSize: 12, height: 1.3),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
