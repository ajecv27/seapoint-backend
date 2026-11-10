# SeaPoint navigation trip recording update. Compatible with Windows PowerShell 5.1.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$sourceHash = 'a6e22b394345337498d5d0b922e544fdcdd95736400cb3abdc0e4ca31a2585c5'
$targetHash = '7a76bbe99e2fdbbc48a6262045c5c4cd6bda5776596af449bd64c92ad57b11d0'
$assetBase = 'https://raw.githubusercontent.com/ajecv27/seapoint-backend/codex/navigation-trip-recording/android-client/navigation/'
$assetHashes = [ordered]@{
    'navigation-patch.json' = '15b434f40440c887a811701c7387bbb496beb4a088b29a870aae2b3ec9d15115'
    'trip_recorder.dart' = '31d2b1f8af055e13b37fb3e3e2ad32ce6563110620f14b0911e1efe2045cd9e0'
    'trip_map.dart' = '9a75b3782ac516f741c49107561729332ff3da9ca8350b92a710966004b62de1'
    'trip_widgets.dart' = 'f58329a06b35ec543f8a56d88507500bc1bbeecc4a1064081597fb0bd8469c9f'
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
function Read-SeaPointManifest([string]$text) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.XmlResolver = $null
    $doc.PreserveWhitespace = $true
    $doc.LoadXml($text)
    if ($doc.DocumentElement.LocalName -ne 'manifest') { throw 'AndroidManifest.xml has no manifest root. No files changed.' }
    return ,$doc
}
function Test-SeaPointPermission($doc, [string]$permission) {
    foreach ($node in $doc.SelectNodes('/manifest/uses-permission')) {
        if ($node.GetAttribute('name', 'http://schemas.android.com/apk/res/android') -eq $permission) { return $true }
    }
    return $false
}

$projectRoot = (Get-Location).ProviderPath
$navigationPath = Join-Path $projectRoot 'lib/navigation_screen.dart'
$manifestPath = Join-Path $projectRoot 'android/app/src/main/AndroidManifest.xml'
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'pubspec.yaml') -PathType Leaf) -or
    !(Test-Path -LiteralPath $navigationPath -PathType Leaf) -or
    !(Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'Run this from the SeaPoint project folder in the Android Studio Terminal.'
}
$navigation = Read-SeaPointText $navigationPath
$existingHash = Get-SeaPointHash ($utf8.GetBytes($navigation))
if ($existingHash -ne $sourceHash -and $existingHash -ne $targetHash) {
    throw 'Navigation differs from the uploaded version. No files changed. Upload your current lib/navigation_screen.dart so it can be updated safely.'
}

$stageDirectory = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-navigation-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stageDirectory)
try {
    # Download and verify everything before changing the project.
    foreach ($name in $assetHashes.Keys) {
        $downloadPath = Join-Path $stageDirectory $name
        Invoke-WebRequest -UseBasicParsing -Uri ($assetBase + $name) -OutFile $downloadPath
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($downloadPath))) -ne $assetHashes[$name]) {
            throw "Downloaded $name did not pass verification. No project files changed."
        }
    }
    $patch = [IO.File]::ReadAllText((Join-Path $stageDirectory 'navigation-patch.json'), $utf8) | ConvertFrom-Json
    if ($patch.format -ne 'seapoint-utf16-delta-v1' -or
        $patch.source_sha256 -ne $sourceHash -or $patch.target_sha256 -ne $targetHash) {
        throw 'Navigation patch version does not match this installer. No files changed.'
    }
    $updatedNavigation = $navigation
    if ($existingHash -eq $sourceHash) {
        foreach ($edit in @($patch.edits | Sort-Object -Property offset -Descending)) {
            $offset = [int]$edit.offset
            $length = [int]$edit.remove_length
            if ($offset -lt 0 -or $length -lt 0 -or $offset + $length -gt $updatedNavigation.Length) {
                throw 'Navigation patch has an invalid range. No files changed.'
            }
            $updatedNavigation = $updatedNavigation.Remove($offset, $length).Insert($offset, [string]$edit.insert)
        }
    }
    if ((Get-SeaPointHash ($utf8.GetBytes($updatedNavigation))) -ne $targetHash) {
        throw 'Navigation patch did not produce the verified result. No files changed.'
    }

    $writes = New-Object 'System.Collections.Generic.List[object]'
    if ($existingHash -ne $targetHash) {
        $writes.Add([pscustomobject]@{ Relative = 'lib/navigation_screen.dart'; Text = $updatedNavigation })
    }
    foreach ($name in @('trip_recorder.dart', 'trip_map.dart', 'trip_widgets.dart')) {
        $relative = 'lib/' + $name
        $destination = Join-Path $projectRoot $relative
        if ((Test-Path -LiteralPath $destination) -and !(Test-Path -LiteralPath $destination -PathType Leaf)) {
            throw "$relative is not a regular file. No files changed."
        }
        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            $helperHash = Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText $destination)))
            if ($helperHash -ne $assetHashes[$name]) {
                throw "$relative already exists with different contents. No files changed; upload it with navigation_screen.dart."
            }
        } else {
            $writes.Add([pscustomobject]@{ Relative = $relative; Text = (Read-SeaPointText (Join-Path $stageDirectory $name)) })
        }
    }

    # Keep the local manifest intact, adding only missing foreground GPS and
    # network permissions. This does not request background location access.
    $manifest = [IO.File]::ReadAllText($manifestPath, $utf8)
    $manifestDoc = Read-SeaPointManifest $manifest
    $permissions = @('android.permission.ACCESS_FINE_LOCATION', 'android.permission.ACCESS_COARSE_LOCATION', 'android.permission.INTERNET')
    $missing = @($permissions | Where-Object { !(Test-SeaPointPermission $manifestDoc $_) })
    if ($missing.Count -gt 0) {
        $rootPattern = [regex]::new('<manifest\b[^>]*>')
        if ($rootPattern.Matches($manifest).Count -ne 1) { throw 'Could not safely locate the manifest opening tag. No files changed.' }
        $newline = "`n"
        if ($manifest.Contains("`r`n")) { $newline = "`r`n" }
        $permissionText = ''
        foreach ($permission in $missing) {
            $permissionText += $newline + '    <uses-permission android:name="' + $permission + '" />'
        }
        $rootMatch = $rootPattern.Match($manifest)
        $manifest = $manifest.Insert($rootMatch.Index + $rootMatch.Length, $permissionText)
        $manifestDoc = Read-SeaPointManifest $manifest
        foreach ($permission in $permissions) {
            if (!(Test-SeaPointPermission $manifestDoc $permission)) { throw 'Android permission validation failed. No files changed.' }
        }
        $writes.Add([pscustomobject]@{ Relative = 'android/app/src/main/AndroidManifest.xml'; Text = $manifest })
    }

    if ($writes.Count -eq 0) {
        Write-Host 'The navigation trip update is already installed. Click Run in Android Studio to load it on your phone.'
        return
    }
    $backupDirectory = Join-Path $projectRoot ('.seapoint-backups/navigation-trip-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
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
        if ((Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText $navigationPath)))) -ne $targetHash) { throw 'Installed navigation did not pass verification.' }
        foreach ($name in @('trip_recorder.dart', 'trip_map.dart', 'trip_widgets.dart')) {
            if ((Get-SeaPointHash ($utf8.GetBytes((Read-SeaPointText (Join-Path $projectRoot ('lib/' + $name)))))) -ne $assetHashes[$name]) { throw "Installed $name did not pass verification." }
        }
        $finalManifest = Read-SeaPointManifest ([IO.File]::ReadAllText($manifestPath, $utf8))
        foreach ($permission in $permissions) {
            if (!(Test-SeaPointPermission $finalManifest $permission)) { throw 'Installed Android permission did not pass verification.' }
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
    Write-Host 'Navigation trip recording installed: boat marker, black GPS trail, knots, GPS course and trip summary.'
    Write-Host ('Backups: ' + $backupDirectory)
    Write-Host 'Run flutter analyze, then click Run in Android Studio to load the update on your phone.'
} finally {
    if (Test-Path -LiteralPath $stageDirectory) { Remove-Item -LiteralPath $stageDirectory -Recurse -Force }
}
