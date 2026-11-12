/// Retains the official synopsis and each labelled forecast period for the
/// source tooltip/cache. Section boundaries prevent winds or metadata leaking
/// into the compact weather outlook.
String extractOfficialWeatherOutlook(String bulletin) {
  const boundary = r'(?=\bWeather\s+(?:today|tonight|tomorrow)\s*:'
      r'|\b(?:Winds|Seas|Rainfall|Sunrise|Sunset|Forecast issued)\s*:|$)';
  String section(String heading) =>
      RegExp(
        '\\b$heading\\s*:\\s*(.*?)$boundary',
        caseSensitive: false,
        dotAll: true,
      ).firstMatch(bulletin)?.group(1)?.trim() ??
      '';

  final synopsis = section('Synopsis');
  final sections = <String>[if (synopsis.isNotEmpty) synopsis];
  for (final period in ['Today', 'Tonight', 'Tomorrow']) {
    final forecast = section('Weather\\s+$period');
    if (forecast.isNotEmpty) sections.add('$period: $forecast');
  }
  return sections.join('\n');
}

/// Prefers the bulletin's own short, complete forecast for the current labelled
/// period. It never infers a period from the phone's clock. If a cached source
/// has only a synopsis, known phrases are shortened conservatively; unfamiliar
/// wording and its qualifications stay together.
String weatherOutlookSynopsis(String outlook) {
  var text = outlook.replaceAll(RegExp(r'\s+'), ' ').trim();
  if (text.isEmpty) return '';

  for (final period in ['Today', 'Tonight', 'Tomorrow']) {
    final forecast = RegExp(
      '(?:^|\\s)$period:\\s*(.*?)(?=\\s+(?:Today|Tonight|Tomorrow):|\$)',
      dotAll: true,
    ).firstMatch(text)?.group(1)?.trim();
    if (forecast != null && forecast.isNotEmpty) {
      return _clipped(forecast)
          ? 'Read the official bulletin for the complete outlook.'
          : '$period: ${_formatCompleteForecast(forecast)}';
    }
  }

  text = text.replaceFirst(
    RegExp(r'^Synopsis\s*:\s*', caseSensitive: false),
    '',
  );
  if (_clipped(text)) {
    return 'Read the official bulletin for the complete outlook.';
  }
  if (RegExp(
    r'^As a drier (?:airmass|air mass) moves into the area, generally stable conditions should return\.\s+However,? as the winds remain light, daytime heating and available moisture may generate periods of cloudiness and showers\.?$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return 'More stable weather is expected, but daytime showers remain possible.';
  }
  return _formatCompleteForecast(text);
}

/// Summarizes the official airmass/synoptic discussion, rather than replacing
/// it with a Today/Tonight forecast. The original period forecasts remain in
/// the cached source and tooltip.
String officialWeatherSynopsis(String outlook) {
  final text = outlook.replaceAll(RegExp(r'\s+'), ' ').trim();
  if (text.isEmpty) return '';
  final synopsis = text
      .split(RegExp(r'(?:^|\s)(?:Today|Tonight|Tomorrow):\s*'))
      .first
      .replaceFirst(RegExp(r'^Synopsis\s*:\s*', caseSensitive: false), '')
      .trim();
  if (synopsis.isEmpty) {
    return 'Official synopsis unavailable; open the bulletin for details.';
  }
  if (_clipped(synopsis)) {
    return 'Read the official bulletin for the complete synopsis.';
  }
  if (RegExp(
    r'^As a drier (?:airmass|air mass) moves into the area, generally stable conditions should return\.\s+However,? as the winds remain light, daytime heating and available moisture may generate periods of cloudiness and showers\.?$',
    caseSensitive: false,
  ).hasMatch(synopsis)) {
    return 'Drier air should bring more stable weather, with daytime showers still possible.';
  }
  return _formatCompleteForecast(synopsis);
}

bool _clipped(String text) => text.endsWith('...') || text.endsWith('…');

String _formatCompleteForecast(String text) => text
    .split(RegExp(r'(?<=[.!?])\s+'))
    .where((sentence) => sentence.trim().isNotEmpty)
    .map(_shortenSentence)
    .join(' ');

String _shortenSentence(String source) {
  var sentence = source.trim();
  if (RegExp(
    r'^As a drier (?:airmass|air mass) moves into the area, generally stable conditions should return[.!]?$',
    caseSensitive: false,
  ).hasMatch(sentence)) {
    return 'Drier air should bring more stable weather.';
  }
  if (RegExp(
    r'^However,? as the winds remain light, daytime heating and available moisture may generate periods of cloudiness and showers[.!]?$',
    caseSensitive: false,
  ).hasMatch(sentence)) {
    return 'Daytime cloud and showers remain possible in light winds.';
  }

  sentence = sentence.replaceAllMapped(
    RegExp(
      r'\b(\d+(?:\.\d+)?)\s+(?:percent|per cent)(?:\s+or\s+(?:slight|low|moderate|high))?\s+chance\b',
      caseSensitive: false,
    ),
    (match) => '${match.group(1)}% chance',
  );
  // Only shorten headline-style conditions. In full sentences the noun is
  // grammatical: "Partly cloudy skies are expected" must keep "skies".
  sentence = sentence.replaceFirstMapped(
    RegExp(
      r'^((?:(?:Today|Tonight|Tomorrow):\s*)?)((?:fair to )?partly cloudy|cloudy|clear) skies(?=\s+with\b|[.!?]?$)',
      caseSensitive: false,
    ),
    (match) => '${match.group(1)}${match.group(2)}',
  );
  if (!RegExp(r'[.!?]$').hasMatch(sentence)) sentence = '$sentence.';
  return sentence;
}
