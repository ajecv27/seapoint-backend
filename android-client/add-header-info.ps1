$path = Join-Path (Get-Location) 'lib\radar_screen.dart'
if (!(Test-Path -LiteralPath $path)) { throw 'Run this from the SeaPoint project folder in Android Studio.' }
$code = [IO.File]::ReadAllText($path)
if ($code.Contains('seapointUseNativeInfo')) {
    if ($code.Contains('minimumSize: const Size(34, 34)')) { Write-Host 'The compact header icon is already installed. Click Run in Android Studio.'; return }
    $existing = [regex]::new("(?s)(tooltip:\s*'Map information and credits',\s*style:\s*IconButton\.styleFrom\()(.*?)(\),\s*icon:\s*const Icon\(Icons\.info_outline\),)")
    if ($existing.Matches($code).Count -ne 1) { throw 'The existing header differs from the expected version. No files changed; upload lib/radar_screen.dart.' }
    $compact = @'
                backgroundColor: const Color(0xA31E2731),
                foregroundColor: Colors.white,
                minimumSize: const Size(34, 34),
                padding: const EdgeInsets.all(7),
              ),
              icon: const Icon(Icons.info_outline, size: 18),
'@
    $updated = $existing.Replace($code, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Groups[1].Value + "`r`n" + $compact }, 1)
    $backup = $path + '.before-compact-info-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak'
    Copy-Item -LiteralPath $path -Destination $backup
    [IO.File]::WriteAllText($path, $updated, [Text.UTF8Encoding]::new($false))
    Write-Host 'Header info icon made smaller. Click Run in Android Studio to update your phone.'
    return
}
$app = [regex]::new("(?s)(appBar:\s*AppBar\s*\(\s*title:\s*const\s+Text\s*\(\s*'SeaPoint Rain Radar'\s*,?\s*\)\s*,)(\s*\)\s*,\s*body:)")
$ready = [regex]::new("if\s*\(message\.message\s*==\s*'ready'\)\s*\{")
if ($app.Matches($code).Count -ne 1 -or $ready.Matches($code).Count -ne 1) { throw 'This radar screen differs from the uploaded version. No files changed; upload lib/radar_screen.dart so its header can be updated safely.' }
$actions = @'
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: IconButton.filled(
              tooltip: 'Map information and credits',
              style: IconButton.styleFrom(
                backgroundColor: const Color(0xA31E2731),
                foregroundColor: Colors.white,
                minimumSize: const Size(34, 34),
                padding: const EdgeInsets.all(7),
              ),
              icon: const Icon(Icons.info_outline, size: 18),
              onPressed: _ready ? () {
                unawaited(_webView.runJavaScript(
                  'window.seapointToggleInfo && window.seapointToggleInfo();',
                ).catchError((_) {}));
              } : null,
            ),
          ),
        ],
'@
$bridge = @'
            unawaited(_webView.runJavaScript(
              'window.seapointUseNativeInfo && window.seapointUseNativeInfo();',
            ).catchError((_) {}));
'@
$updated = $app.Replace($code, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Groups[1].Value + "`r`n" + $actions + $m.Groups[2].Value }, 1)
$updated = $ready.Replace($updated, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Value + "`r`n" + $bridge }, 1)
$backup = $path + '.before-header-info-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak'
Copy-Item -LiteralPath $path -Destination $backup
[IO.File]::WriteAllText($path, $updated, [Text.UTF8Encoding]::new($false))
Write-Host 'Header info button installed. Click Run in Android Studio to update your phone.'
