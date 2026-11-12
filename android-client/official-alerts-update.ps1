# SeaPoint official alerts and island outlook. Compatible with Windows PowerShell 5.1.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$assetBase = 'https://raw.githubusercontent.com/ajecv27/seapoint-backend/codex/navigation-trip-recording/android-client/official-alerts/'
$fileTargets = [ordered]@{
    'lib/main.dart' = @{ Target = '2762831b83ab6c33a22ce1f4a45ba442cc412976208b3b689aabd745525612b5'; Sources = @{
        'd8cbfbcc2fdaa09861297951f65af28ee95a64dba0519b5164d3024078020397' = 'main-combined-patch.json'
        'f8b8e835a547660a0439cf29e626aaebb733282665c69e5d45aa39c87507630e' = 'main-polish-patch.json'
    } }
}

$helperTargets = [ordered]@{
    'lib/weather_synopsis.dart' = @{ Asset = 'weather_synopsis.dart'; Target = 'c3f9a41e288e26419bc310eebc42cf50c3e5828ea4488af0f01deb43cf867688'; RequiredExisting = $true; Sources = @('bf39ff7471ed60d75457c85fc84c654ef7eeccee544a10954184f17b9a05f99e') }
    'lib/official_weather_card.dart' = @{ Asset = 'official_weather_card.dart'; Target = '8cbaf52f4f04102a63acb45462a0018ffffacee9b2a13588931159a264df7724'; RequiredExisting = $false; Sources = @('4b29e827d1643d227adaf696bc17b2386ccbf2056782545f3783c10091427502'); MissingAllowedMainSources = @('f8b8e835a547660a0439cf29e626aaebb733282665c69e5d45aa39c87507630e','2762831b83ab6c33a22ce1f4a45ba442cc412976208b3b689aabd745525612b5') }
    'lib/official_alert_feed.dart' = @{ Asset = 'official_alert_feed.dart'; Target = '1abc27c754957c2f9c78cbd0fa647642894e198b7e3d6fcf360017bbfd4dbd34'; RequiredExisting = $false; Sources = @() }
}

$assetHashes = [ordered]@{
    'main-combined-patch.json' = '0392bf8dc77a128cb5486bbf3082e83b774a388fb371982e26c9eba34d6cfeff'
    'main-polish-patch.json' = 'fe87df663ac91299e9f46b42a8bd388a0412d93e611550e48bcfb426c486d063'
    'weather_synopsis.dart' = 'c3f9a41e288e26419bc310eebc42cf50c3e5828ea4488af0f01deb43cf867688'
    'official_weather_card.dart' = '8cbaf52f4f04102a63acb45462a0018ffffacee9b2a13588931159a264df7724'
    'official_alert_feed.dart' = '1abc27c754957c2f9c78cbd0fa647642894e198b7e3d6fcf360017bbfd4dbd34'
}

$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
function Normalize-SeaPointText([string]$text) {
    return $text.Replace("`r`n", "`n").Replace("`r", "`n").TrimStart([char]0xFEFF)
}
function Get-SeaPointHash([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Read-SeaPointText([string]$path) {
    return Normalize-SeaPointText ([IO.File]::ReadAllText($path, $utf8))
}
$projectRoot = (Get-Location).ProviderPath
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'pubspec.yaml') -PathType Leaf)) {
    throw 'Run this from the SeaPoint project folder in the Android Studio Terminal.'
}
$currentFiles = @{}
# Validate every supported client file before downloads or writes.
foreach ($relative in $fileTargets.Keys) {
    $path = Join-Path $projectRoot $relative
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "$relative is missing. No files changed." }
    $text = Read-SeaPointText $path
    $hash = Get-SeaPointHash ($utf8.GetBytes($text))
    $spec = $fileTargets[$relative]
    if ($hash -ne $spec.Target -and !$spec.Sources.ContainsKey($hash)) {
        throw "$relative differs from the supported SeaPoint version. No files changed; share the current file so it can be updated safely. Install the previous weather and navigation update before this update."
    }
    $currentFiles[$relative] = @{ Text = $text; Hash = $hash }
}
$currentHelpers = @{}
foreach ($relative in $helperTargets.Keys) {
    $path = Join-Path $projectRoot $relative
    $spec = $helperTargets[$relative]
    $exists = Test-Path -LiteralPath $path
    if ($exists -and !(Test-Path -LiteralPath $path -PathType Leaf)) { throw "$relative is not a regular file. No files changed." }
    if (!$exists -and $spec.RequiredExisting) { throw "$relative is missing. Install the previous weather and navigation update first. No files changed." }
    if (!$exists -and $spec.ContainsKey('MissingAllowedMainSources') -and
        $spec.MissingAllowedMainSources -notcontains $currentFiles['lib/main.dart'].Hash) {
        throw "$relative is missing for the installed weather screen version. No files changed."
    }
    $hash = $null
    if ($exists) {
        $hash = Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText $path)))
        if ($hash -ne $spec.Target -and $spec.Sources -notcontains $hash) {
            throw "$relative contains unrecognized changes. No files changed; share the current file so it can be updated safely."
        }
    }
    $currentHelpers[$relative] = @{ Exists = $exists; Hash = $hash }
}
$stageDirectory = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-official-alerts-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stageDirectory)
try {
    foreach ($name in $assetHashes.Keys) {
        $downloadPath = Join-Path $stageDirectory $name
        Invoke-WebRequest -UseBasicParsing -Uri ($assetBase + $name) -OutFile $downloadPath
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($downloadPath))) -ne $assetHashes[$name]) {
            throw "Downloaded $name did not pass verification. No project files changed."
        }
    }
    $writes = New-Object 'System.Collections.Generic.List[object]'
    foreach ($relative in $fileTargets.Keys) {
        $spec = $fileTargets[$relative]
        $current = $currentFiles[$relative]
        if ($current.Hash -eq $spec.Target) { continue }
        $patchPath = Join-Path $stageDirectory $spec.Sources[$current.Hash]
        $patch = [IO.File]::ReadAllText($patchPath, $utf8) | ConvertFrom-Json
        if ($patch.format -ne 'seapoint-utf16-delta-v1' -or $patch.source_sha256 -ne $current.Hash -or $patch.target_sha256 -ne $spec.Target) {
            throw "$relative patch version did not match this installer. No files changed."
        }
        $updated = $current.Text
        foreach ($edit in @($patch.edits | Sort-Object -Property offset -Descending)) {
            $offset = [int]$edit.offset
            $length = [int]$edit.remove_length
            if ($offset -lt 0 -or $length -lt 0 -or $offset + $length -gt $updated.Length) {
                throw "$relative patch contains an invalid range. No files changed."
            }
            $updated = $updated.Remove($offset, $length).Insert($offset, [string]$edit.insert)
        }
        if ((Get-SeaPointHash ($utf8.GetBytes($updated))) -ne $spec.Target) { throw "$relative patch result did not pass verification. No files changed." }
        $writes.Add([pscustomobject]@{ Relative = $relative; Text = $updated })
    }
    foreach ($relative in $helperTargets.Keys) {
        $spec = $helperTargets[$relative]
        if ($currentHelpers[$relative].Hash -eq $spec.Target) { continue }
        $text = Read-SeaPointText (Join-Path $stageDirectory $spec.Asset)
        if ((Get-SeaPointHash ($utf8.GetBytes($text))) -ne $spec.Target) { throw "$relative content did not pass verification. No files changed." }
        $writes.Add([pscustomobject]@{ Relative = $relative; Text = $text })
    }
    if ($writes.Count -eq 0) {
        Write-Host 'The official alerts and outlook update is already installed. Click Run in Android Studio to load it on your phone.'
        return
    }
    $backupDirectory = Join-Path $projectRoot ('.seapoint-backups/official-alerts-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    $null = [IO.Directory]::CreateDirectory($backupDirectory)
    $prepared = New-Object 'System.Collections.Generic.List[object]'
    foreach ($write in $writes) {
        $destination = Join-Path $projectRoot $write.Relative
        $existed = Test-Path -LiteralPath $destination -PathType Leaf
        $oldBytes = $null
        if ($existed) {
            $oldBytes = [IO.File]::ReadAllBytes($destination)
            $backupPath = Join-Path $backupDirectory ($write.Relative + '.bak')
            $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($backupPath))
            [IO.File]::WriteAllBytes($backupPath, $oldBytes)
        }
        $prepared.Add([pscustomobject]@{ Path = $destination; Text = $write.Text; Existed = $existed; OldBytes = $oldBytes })
    }
    $applied = New-Object 'System.Collections.Generic.List[object]'
    try {
        foreach ($write in $prepared) {
            $applied.Add($write)
            [IO.File]::WriteAllText($write.Path, $write.Text, $utf8)
        }
        foreach ($relative in $fileTargets.Keys) {
            if ((Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText (Join-Path $projectRoot $relative))))) -ne $fileTargets[$relative].Target) {
                throw "Installed $relative did not pass verification."
            }
        }
        foreach ($relative in $helperTargets.Keys) {
            if ((Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText (Join-Path $projectRoot $relative))))) -ne $helperTargets[$relative].Target) {
                throw "Installed $relative did not pass verification."
            }
        }
    } catch {
        $installError = $_
        $rollbackErrors = New-Object 'System.Collections.Generic.List[string]'
        for ($i = $applied.Count - 1; $i -ge 0; $i--) {
            $write = $applied[$i]
            try {
                if ($write.Existed) { [IO.File]::WriteAllBytes($write.Path, $write.OldBytes) }
                elseif (Test-Path -LiteralPath $write.Path) { Remove-Item -LiteralPath $write.Path -Force }
            } catch { $rollbackErrors.Add($write.Path) }
        }
        if ($rollbackErrors.Count -gt 0) { throw "Update failed and some files could not be restored: $($rollbackErrors -join ', '). Backups: $backupDirectory. Original error: $installError" }
        throw "Update failed; project files were restored. Backups: $backupDirectory. Original error: $installError"
    }
    Write-Host 'SeaPoint official alerts and island outlook installed.'
    Write-Host ('Backups: ' + $backupDirectory)
    Write-Host 'Run flutter analyze, then click Run in Android Studio to load the update on your phone.'
} finally {
    if (Test-Path -LiteralPath $stageDirectory) { Remove-Item -LiteralPath $stageDirectory -Recurse -Force }
}
