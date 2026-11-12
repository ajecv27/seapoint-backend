# SeaPoint weather and navigation polish. Compatible with Windows PowerShell 5.1.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$assetBase = 'https://raw.githubusercontent.com/ajecv27/seapoint-backend/codex/navigation-trip-recording/android-client/weather-navigation/'
$fileTargets = [ordered]@{
    'lib/main.dart' = @{ Target = 'f8b8e835a547660a0439cf29e626aaebb733282665c69e5d45aa39c87507630e'; Sources = @{
        '39a08fdcb844bde1b1b1f16a2b5ba5d692da79076908cf79acc89a8688bd626d' = 'main-original-patch.json'
        'a70d285b7b1db6b8b776b307b45a6f5deab9cf6a1c12e0af97d90bdad64c36d1' = 'main-compact-patch.json'
    } }
    'lib/navigation_screen.dart' = @{ Target = '094c43d262e230039cba15215072c7d78c9c6e08cf0eccf1929ea8838b94556c'; Sources = @{
        '7a76bbe99e2fdbbc48a6262045c5c4cd6bda5776596af449bd64c92ad57b11d0' = 'navigation-patch.json'
    } }
}

$helperTargets = [ordered]@{
    'lib/weather_synopsis.dart' = @{ Asset = 'weather_synopsis.dart'; Target = 'bf39ff7471ed60d75457c85fc84c654ef7eeccee544a10954184f17b9a05f99e'; RequiredExisting = $false; Sources = @() }
    'lib/trip_map.dart' = @{ Asset = 'trip_map.dart'; Target = 'ec86f529161268bbd7353c9fb40428b90c14ae259a97f85a97c2da384ef4360b'; RequiredExisting = $true; Sources = @('9a75b3782ac516f741c49107561729332ff3da9ca8350b92a710966004b62de1') }
}

$assetHashes = [ordered]@{
    'main-original-patch.json' = 'd0633481d732d2ace07b9f02096e5e9d3e9b05049b1b7b262312c4d0c55158ac'
    'main-compact-patch.json' = '7da154f1c9e93e9d7a971d8ff72e00fbdb2218648b01caabfaa838fd26bc8298'
    'navigation-patch.json' = 'd1aff48dd0e17d6b42875a95c6666210956eb8bde8712831654c9dc2e319ad8d'
    'weather_synopsis.dart' = 'bf39ff7471ed60d75457c85fc84c654ef7eeccee544a10954184f17b9a05f99e'
    'trip_map.dart' = 'ec86f529161268bbd7353c9fb40428b90c14ae259a97f85a97c2da384ef4360b'
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
# Validate BOTH screens before downloads or writes, including partial reruns.
foreach ($relative in $fileTargets.Keys) {
    $path = Join-Path $projectRoot $relative
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "$relative is missing. No files changed." }
    $text = Read-SeaPointText $path
    $hash = Get-SeaPointHash ($utf8.GetBytes($text))
    $spec = $fileTargets[$relative]
    if ($hash -ne $spec.Target -and !$spec.Sources.ContainsKey($hash)) {
        throw "$relative differs from the supported SeaPoint version. No files changed; share the current file so it can be updated safely. Navigation requires the trip-recording update."
    }
    $currentFiles[$relative] = @{ Text = $text; Hash = $hash }
}
$currentHelpers = @{}
foreach ($relative in $helperTargets.Keys) {
    $path = Join-Path $projectRoot $relative
    $spec = $helperTargets[$relative]
    $exists = Test-Path -LiteralPath $path
    if ($exists -and !(Test-Path -LiteralPath $path -PathType Leaf)) { throw "$relative is not a regular file. No files changed." }
    if (!$exists -and $spec.RequiredExisting) { throw "$relative is missing. Install the navigation trip-recording update first. No files changed." }
    $hash = $null
    if ($exists) {
        $hash = Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText $path)))
        if ($hash -ne $spec.Target -and $spec.Sources -notcontains $hash) {
            throw "$relative contains unrecognized changes. No files changed; share the current file so it can be updated safely."
        }
    }
    $currentHelpers[$relative] = @{ Exists = $exists; Hash = $hash }
}
# Existing trip calculations and widgets stay local and are never overwritten.
foreach ($relative in @('lib/trip_recorder.dart', 'lib/trip_widgets.dart')) {
    if (!(Test-Path -LiteralPath (Join-Path $projectRoot $relative) -PathType Leaf)) {
        throw "$relative is missing. Install the navigation trip-recording update first. No files changed."
    }
}
$stageDirectory = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-ui-polish-' + [Guid]::NewGuid().ToString('N'))
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
        Write-Host 'The weather and navigation polish is already installed. Click Run in Android Studio to load it on your phone.'
        return
    }
    $backupDirectory = Join-Path $projectRoot ('.seapoint-backups/weather-navigation-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
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
    Write-Host 'SeaPoint weather and navigation polish installed.'
    Write-Host ('Backups: ' + $backupDirectory)
    Write-Host 'Run flutter analyze, then click Run in Android Studio to load the update on your phone.'
} finally {
    if (Test-Path -LiteralPath $stageDirectory) { Remove-Item -LiteralPath $stageDirectory -Recurse -Force }
}
