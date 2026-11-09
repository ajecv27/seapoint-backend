$path = Join-Path (Get-Location) 'lib\radar_screen.dart'
if (!(Test-Path -LiteralPath $path)) { throw 'Run this from the SeaPoint project folder in Android Studio.' }
$code = [IO.File]::ReadAllText($path)
if ($code.Contains('seapointUseNativeInfo')) { Write-Host 'The header info button is already installed. Click Run in Android Studio.'; return }
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
              ),
              icon: const Icon(Icons.info_outline),
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
