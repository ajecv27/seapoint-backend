# SeaPoint confirmed no-alert wording update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$assetUrl = 'https://raw.githubusercontent.com/ajecv27/seapoint-backend/codex/navigation-trip-recording/android-client/alert-wording/official_alert_feed.dart'
$sourceHashes = @('1abc27c754957c2f9c78cbd0fa647642894e198b7e3d6fcf360017bbfd4dbd34', '2e087829bb01bf470fef4ddfd64da179c12a63f4c16f3adb032a5edd9ec16b04')
$targetHash = 'ed8a1e0679932fc64e34f201d7fa58995e653a3e7073d211706b2aed615d8774'
$relativePath = 'lib/official_alert_feed.dart'
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)

function Get-SeaPointHash([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-SeaPointTextHash([byte[]]$bytes) {
    $text = $utf8.GetString($bytes).TrimStart([char]0xFEFF).Replace("`r`n", "`n").Replace("`r", "`n")
    return Get-SeaPointHash ($utf8.GetBytes($text))
}

$projectRoot = (Get-Location).ProviderPath
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'pubspec.yaml') -PathType Leaf)) {
    throw 'Run this from the SeaPoint project folder in the Android Studio Terminal. No files changed.'
}
$targetPath = Join-Path $projectRoot $relativePath
if (!(Test-Path -LiteralPath $targetPath -PathType Leaf)) {
    throw 'lib/official_alert_feed.dart is missing or is not a regular file. Install the official alerts update first. No files changed.'
}
$originalBytes = [IO.File]::ReadAllBytes($targetPath)
$originalHash = Get-SeaPointHash $originalBytes
$currentHash = Get-SeaPointTextHash $originalBytes
if ($currentHash -eq $targetHash) {
    Write-Host 'The SeaPoint alert wording update is already installed. Click Run in Android Studio to load it on your phone.'
    return
}
if ($sourceHashes -notcontains $currentHash) {
    throw 'lib/official_alert_feed.dart contains unrecognized changes. No files changed; share the current file so it can be updated safely.'
}

$stageDirectory = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-alert-wording-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stageDirectory)
try {
    $downloadPath = Join-Path $stageDirectory 'official_alert_feed.dart'
    Invoke-WebRequest -UseBasicParsing -Uri $assetUrl -OutFile $downloadPath
    $payloadBytes = [IO.File]::ReadAllBytes($downloadPath)
    if ((Get-SeaPointHash $payloadBytes) -ne $targetHash -or (Get-SeaPointTextHash $payloadBytes) -ne $targetHash) {
        throw 'Downloaded alert status file did not pass verification. No project files changed.'
    }
    if (!(Test-Path -LiteralPath $targetPath -PathType Leaf) -or (Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $originalHash) {
        throw 'lib/official_alert_feed.dart changed while the update was downloading. No project files changed.'
    }

    $backupDirectory = Join-Path $projectRoot ('.seapoint-backups/alert-wording-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
    $null = [IO.Directory]::CreateDirectory($backupDirectory)
    $backupPath = Join-Path $backupDirectory 'official_alert_feed.dart.bak'
    [IO.File]::WriteAllBytes($backupPath, $originalBytes)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $originalHash) {
        throw "The alert status backup did not pass verification. No project files changed. Backup: $backupPath"
    }

    try {
        [IO.File]::WriteAllBytes($targetPath, $payloadBytes)
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $targetHash) {
            throw 'Installed lib/official_alert_feed.dart did not pass verification.'
        }
    } catch {
        $installError = $_
        try {
            [IO.File]::WriteAllBytes($targetPath, $originalBytes)
            if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $originalHash) {
                throw 'Restored file did not pass verification.'
            }
        } catch {
            throw "Update failed and the original file could not be restored. Restore the backup: $backupPath. Original error: $installError. Restore error: $_"
        }
        throw "Update failed; the original file was restored. Backup: $backupPath. Original error: $installError"
    }

    Write-Host 'SeaPoint confirmed no-alert wording update installed.'
    Write-Host ('Backup: ' + $backupPath)
    Write-Host 'Run flutter analyze, then click Run in Android Studio to load the update on your phone.'
} finally {
    if (Test-Path -LiteralPath $stageDirectory) { Remove-Item -LiteralPath $stageDirectory -Recurse -Force }
}
