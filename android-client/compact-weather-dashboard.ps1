$path = Join-Path (Get-Location) 'lib\main.dart'
if (!(Test-Path -LiteralPath $path)) { throw 'Run this from the SeaPoint project folder in Android Studio.' }
$code = [IO.File]::ReadAllText($path)
if ($code.Contains("'Island Weather Outlook'") -and !$code.Contains('_updateStatus(')) { Write-Host 'The compact Weather dashboard is already installed. Click Run in Android Studio.'; return }
$card = [regex]::new("(?s)Card\(\s*child:\s*ListTile\(\s*leading:\s*const Icon\(\s*Icons\.thunderstorm_outlined,.*?'Weather Systems & Island Outlook'.*?\)\s*,\s*_updateStatus\(\),")
$status = [regex]::new('(?s)  Widget _updateStatus\(\) \{.*?(?=  String directionName\(double degrees\))')
$ages = [regex]::new('(?s)  bool _stale\(DateTime\? time, Duration allowed\) \{.*?(?=  @override\s+void initState\(\))')
foreach ($pattern in @($card, $status, $ages)) {
    if ($pattern.Matches($code).Count -ne 1) { throw 'This dashboard differs from the uploaded version. No files changed; upload lib/main.dart so it can be updated safely.' }
}
$outlook = @'
Card(
                  child: ListTile(
                    dense: true,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 4,
                    ),
                    leading: const Icon(
                      Icons.thunderstorm_outlined,
                      size: 22,
                      color: Color(0xFF087D9D),
                    ),
                    title: const Text(
                      'Island Weather Outlook',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    subtitle: Tooltip(
                      message: 'Antigua & Barbuda Meteorological Service\n'
                          'Issued: ${_officialOutlookIssued ?? 'unverified'}\n'
                          'Checked: ${_clock(_officialBulletinChecked)}\n'
                          '${_officialOutlookVerifiedToday ? 'Current forecast outlook' : 'Validity unverified'}\n'
                          'Outlooks are separate from active warnings.',
                      child: Text(
                        _officialOutlook.isEmpty
                            ? (_officialBulletinUnavailable
                                ? 'Official bulletin unavailable; pull down to retry.'
                                : 'Checking the official island forecast…')
                            : _officialOutlookVerifiedToday
                                ? _officialOutlook
                                : 'Validity unverified · $_officialOutlook',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12, height: 1.25),
                      ),
                    ),
                    trailing: const Icon(Icons.open_in_new, size: 17),
                    onTap: () => launchUrl(
                      Uri.parse('https://www.antiguamet.com/Daily_FCast.html'),
                    ),
                  ),
                ),
'@
$updated = $card.Replace($code, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $outlook }, 1)
$updated = $status.Replace($updated, '', 1)
$updated = $ages.Replace($updated, '', 1)
$backup = $path + '.before-compact-weather-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak'
Copy-Item -LiteralPath $path -Destination $backup
[IO.File]::WriteAllText($path, $updated, [Text.UTF8Encoding]::new($false))
Write-Host 'Compact Weather dashboard installed; refresh and cache logic preserved. Run flutter analyze, then click Run in Android Studio.'
