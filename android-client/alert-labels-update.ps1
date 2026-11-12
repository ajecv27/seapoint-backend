# SeaPoint short alert labels and cached refresh update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$assetUrl = 'https://raw.githubusercontent.com/ajecv27/seapoint-backend/codex/navigation-trip-recording/android-client/alert-labels/official_alert_feed.dart'
$sourceHashes = @('1abc27c754957c2f9c78cbd0fa647642894e198b7e3d6fcf360017bbfd4dbd34', '2e087829bb01bf470fef4ddfd64da179c12a63f4c16f3adb032a5edd9ec16b04', 'ed8a1e0679932fc64e34f201d7fa58995e653a3e7073d211706b2aed615d8774', '1d84c8cdb63fd0f21f540124e2fa8f3a73cc4f412b280c8054a5befc957bf168')
$targetHash = '74f28f95c275da29d6cd9c4ed542d72d73b78ba4020846179ee07f820d105e68'
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$mainPatches = @($utf8.GetString([Convert]::FromBase64String('WwogIHsKICAgICJuYW1lIjogImluaXRpYWwtY2hlY2tpbmctbGFiZWwiLAogICAgIm9sZCI6ICIgIFN0cmluZyBvZmZpY2lhbEFsZXJ0U3RhdHVzID0gJ0NoZWNraW5nIG9mZmljaWFsIGFsZXJ0cy4uLic7IiwKICAgICJuZXciOiAiICBTdHJpbmcgb2ZmaWNpYWxBbGVydFN0YXR1cyA9ICdDaGVja2luZyBhbGVydHPigKYnOyIKICB9LAogIHsKICAgICJuYW1lIjogImZpcnN0LXJlZnJlc2gtY2hlY2tpbmctbGFiZWwiLAogICAgIm9sZCI6ICIgICAgICAgICAgPz8gJ0NoZWNraW5nIG9mZmljaWFsIGFsZXJ0IGNvdmVyYWdlLi4uJzsiLAogICAgIm5ldyI6ICIgICAgICAgICAgPz8gJ0NoZWNraW5nIGFsZXJ0c+KApic7IgogIH0sCiAgewogICAgIm5hbWUiOiAicmVmcmVzaC1yZXN0b3JlZC1yZXBvcnRzIiwKICAgICJvbGQiOiAiICAgICAgICBfZHVlKFxuICAgICAgICAgIF9hbGVydHNDaGVja2VkLFxuICAgICAgICAgIF9sYXN0QWxlcnRzQXR0ZW1wdCxcbiAgICAgICAgICBfd2FybmluZ0ludGVydmFsLFxuICAgICAgICApKSIsCiAgICAibmV3IjogIiAgICAgICAgc2hvdWxkUmVmcmVzaE9mZmljaWFsQWxlcnRzKFxuICAgICAgICAgIG5vdzogbm93LFxuICAgICAgICAgIGNoZWNrZWRBdDogX2FsZXJ0c0NoZWNrZWQsXG4gICAgICAgICAgYXR0ZW1wdGVkQXQ6IF9sYXN0QWxlcnRzQXR0ZW1wdCxcbiAgICAgICAgICBmcm9tQ2FjaGU6IF9vZmZpY2lhbEFsZXJ0c0FyZUNhY2hlZCxcbiAgICAgICAgICByZWZyZXNoSW50ZXJ2YWw6IF93YXJuaW5nSW50ZXJ2YWwsXG4gICAgICAgICAgcmV0cnlJbnRlcnZhbDogX3JldHJ5SW50ZXJ2YWwsXG4gICAgICAgICkpIgogIH0sCiAgewogICAgIm5hbWUiOiAibGF0ZS1jYWNoZS1ndWFyZCIsCiAgICAib2xkIjogIiAgICAgIGlmICghbW91bnRlZCkgcmV0dXJuO1xuICAgICAgZmluYWwgcmVzdG9yZWQgPSByZXBvcnQudmFsaWRDYWNoZWRBbGVydHNBdChEYXRlVGltZS5ub3coKSwgZmFsbGJhY2tDaGVja2VkQXQ6IHNhdmVkKTtcbiAgICAgIHNldFN0YXRlKCgpIHsiLAogICAgIm5ldyI6ICIgICAgICBpZiAoIW1vdW50ZWQpIHJldHVybjtcbiAgICAgIC8vIEEgc2xvd2VyIHByZWZlcmVuY2VzIHJlYWQgbXVzdCBub3QgcmVwbGFjZSBhIGxpdmUgcmVwb3J0IHJlY2VpdmVkIG1lYW53aGlsZS5cbiAgICAgIGlmIChfb2ZmaWNpYWxBbGVydFJlcG9ydCAhPSBudWxsICYmXG4gICAgICAgICAgIV9vZmZpY2lhbEFsZXJ0c0FyZUNhY2hlZCAmJlxuICAgICAgICAgIF9hbGVydHNDaGVja2VkICE9IG51bGwpIHtcbiAgICAgICAgcmV0dXJuO1xuICAgICAgfVxuICAgICAgZmluYWwgcmVzdG9yZWQgPSByZXBvcnQudmFsaWRDYWNoZWRBbGVydHNBdChEYXRlVGltZS5ub3coKSwgZmFsbGJhY2tDaGVja2VkQXQ6IHNhdmVkKTtcbiAgICAgIHNldFN0YXRlKCgpIHsiCiAgfQpdCg==')) | ConvertFrom-Json)

function Get-SeaPointHash([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-SeaPointTextHash([byte[]]$bytes) {
    $text = $utf8.GetString($bytes).TrimStart([char]0xFEFF).Replace("`r`n", "`n").Replace("`r", "`n")
    return Get-SeaPointHash ($utf8.GetBytes($text))
}

function Get-SeaPointOriginalOffset([int]$normalizedOffset, $crlfPositions) {
    $extra = 0
    foreach ($position in $crlfPositions) {
        if ($position -ge $normalizedOffset) { break }
        $extra++
    }
    return $normalizedOffset + $extra
}

function Get-SeaPointPatchedMain([byte[]]$bytes) {
    $body = $utf8.GetString($bytes)
    $bom = ''
    while ($body.Length -gt 0 -and $body[0] -eq [char]0xFEFF) {
        $bom += [char]0xFEFF
        $body = $body.Substring(1)
    }
    $normalized = $body.Replace("`r`n", "`n").Replace("`r", "`n")
    foreach ($marker in @("import 'official_alert_feed.dart';", 'class SeaPointApp', '_restoreCachedAlerts', 'fetchOfficialAlerts', '_warningInterval')) {
        $count = [regex]::Matches($normalized, [regex]::Escape($marker)).Count
        if ($count -lt 1 -or (($marker -eq "import 'official_alert_feed.dart';" -or $marker -eq 'class SeaPointApp') -and $count -ne 1)) {
            throw 'lib/main.dart is not the expected SeaPoint app. No files changed.'
        }
    }

    # Count every patch against the same original text, before replacing anything.
    $ranges = @()
    foreach ($patch in $mainPatches) {
        if ([string]::IsNullOrEmpty($patch.old) -or [string]::IsNullOrEmpty($patch.new) -or $patch.old -eq $patch.new) {
            throw 'The main.dart patch definition is invalid. No files changed.'
        }
        $oldMatches = [regex]::Matches($normalized, [regex]::Escape([string]$patch.old))
        $newMatches = [regex]::Matches($normalized, [regex]::Escape([string]$patch.new))
        if ($oldMatches.Count -eq 1 -and $newMatches.Count -eq 0) {
            $ranges += [PSCustomObject]@{ Start = $oldMatches[0].Index; Length = $oldMatches[0].Length; New = [string]$patch.new; Name = [string]$patch.name }
        } elseif ($oldMatches.Count -ne 0 -or $newMatches.Count -ne 1) {
            throw ('lib/main.dart contains a missing or ambiguous update block: ' + $patch.name + '. No files changed.')
        }
    }
    $sorted = @($ranges | Sort-Object Start)
    $previousEnd = -1
    foreach ($range in $sorted) {
        if ($range.Start -lt $previousEnd) { throw 'lib/main.dart update blocks overlap. No files changed.' }
        $previousEnd = $range.Start + $range.Length
    }
    if ($ranges.Count -eq 0) { return ,$bytes }

    # Map normalized boundaries back to the original string. Unpatched text, mixed
    # line endings, and any original UTF-8 BOM remain exactly as supplied.
    $crlfPositions = New-Object 'System.Collections.Generic.List[int]'
    foreach ($newline in [regex]::Matches($body, "`r`n")) {
        $crlfPositions.Add($newline.Index - $crlfPositions.Count)
    }
    $defaultNewLine = [regex]::Match($body, "`r`n|`n|`r").Value
    if ($defaultNewLine.Length -eq 0) { $defaultNewLine = "`n" }
    foreach ($range in @($ranges | Sort-Object Start -Descending)) {
        $start = Get-SeaPointOriginalOffset $range.Start $crlfPositions
        $end = Get-SeaPointOriginalOffset ($range.Start + $range.Length) $crlfPositions
        $originalBlock = $body.Substring($start, $end - $start)
        $newLine = [regex]::Match($originalBlock, "`r`n|`n|`r").Value
        if ($newLine.Length -eq 0) { $newLine = $defaultNewLine }
        $replacement = $range.New.Replace("`n", $newLine)
        $body = $body.Substring(0, $start) + $replacement + $body.Substring($end)
    }
    return ,($utf8.GetBytes($bom + $body))
}

$projectRoot = (Get-Location).ProviderPath
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'pubspec.yaml') -PathType Leaf)) {
    throw 'Run this from the SeaPoint project folder in the Android Studio Terminal. No files changed.'
}
$targetPath = Join-Path $projectRoot 'lib/official_alert_feed.dart'
$mainPath = Join-Path $projectRoot 'lib/main.dart'
if (!(Test-Path -LiteralPath $targetPath -PathType Leaf)) {
    throw 'lib/official_alert_feed.dart is missing or is not a regular file. Install the official alerts update first. No files changed.'
}
if (!(Test-Path -LiteralPath $mainPath -PathType Leaf)) {
    throw 'lib/main.dart is missing or is not a regular file. No files changed.'
}
$originalBytes = [IO.File]::ReadAllBytes($targetPath)
$originalHash = Get-SeaPointHash $originalBytes
$currentHash = Get-SeaPointTextHash $originalBytes
if ($currentHash -ne $targetHash -and $sourceHashes -notcontains $currentHash) {
    throw 'lib/official_alert_feed.dart contains unrecognized changes. No files changed; share the current file so it can be updated safely.'
}
$mainOriginalBytes = [IO.File]::ReadAllBytes($mainPath)
$mainOriginalHash = Get-SeaPointHash $mainOriginalBytes
$mainPayloadBytes = Get-SeaPointPatchedMain $mainOriginalBytes
$mainTargetHash = Get-SeaPointHash $mainPayloadBytes
if ($currentHash -eq $targetHash -and $mainOriginalHash -eq $mainTargetHash) {
    Write-Host 'The SeaPoint alert label update is already installed. Click Run in Android Studio to load it on your phone.'
    return
}

$stageDirectory = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-alert-labels-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stageDirectory)
try {
    $payloadBytes = $originalBytes
    if ($currentHash -ne $targetHash) {
        $downloadPath = Join-Path $stageDirectory 'official_alert_feed.dart'
        Invoke-WebRequest -UseBasicParsing -Uri $assetUrl -OutFile $downloadPath
        $payloadBytes = [IO.File]::ReadAllBytes($downloadPath)
        if ((Get-SeaPointHash $payloadBytes) -ne $targetHash -or (Get-SeaPointTextHash $payloadBytes) -ne $targetHash) {
            throw 'Downloaded alert status file did not pass verification. No project files changed.'
        }
    }
    $payloadHash = Get-SeaPointHash $payloadBytes
    if (!(Test-Path -LiteralPath $targetPath -PathType Leaf) -or (Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $originalHash -or
        !(Test-Path -LiteralPath $mainPath -PathType Leaf) -or (Get-SeaPointHash ([IO.File]::ReadAllBytes($mainPath))) -ne $mainOriginalHash) {
        throw 'The alert helper or lib/main.dart changed while the update was downloading. No project files changed.'
    }

    $backupDirectory = Join-Path $projectRoot ('.seapoint-backups/alert-labels-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
    $null = [IO.Directory]::CreateDirectory($backupDirectory)
    $backupPath = Join-Path $backupDirectory 'official_alert_feed.dart.bak'
    $mainBackupPath = Join-Path $backupDirectory 'main.dart.bak'
    [IO.File]::WriteAllBytes($backupPath, $originalBytes)
    [IO.File]::WriteAllBytes($mainBackupPath, $mainOriginalBytes)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $originalHash -or
        (Get-SeaPointHash ([IO.File]::ReadAllBytes($mainBackupPath))) -ne $mainOriginalHash) {
        throw "The alert update backup did not pass verification. No project files changed. Backups: $backupDirectory"
    }
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $originalHash -or
        (Get-SeaPointHash ([IO.File]::ReadAllBytes($mainPath))) -ne $mainOriginalHash) {
        throw "The alert helper or lib/main.dart changed before installation. No project files changed. Backups: $backupDirectory"
    }

    try {
        [IO.File]::WriteAllBytes($targetPath, $payloadBytes)
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $payloadHash) {
            throw 'Installed lib/official_alert_feed.dart did not pass verification.'
        }
        [IO.File]::WriteAllBytes($mainPath, $mainPayloadBytes)
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($mainPath))) -ne $mainTargetHash) {
            throw 'Installed lib/main.dart did not pass verification.'
        }
    } catch {
        $installError = $_
        $restoreErrors = @()
        try {
            [IO.File]::WriteAllBytes($targetPath, $originalBytes)
            if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($targetPath))) -ne $originalHash) { throw 'Restored alert helper did not pass verification.' }
        } catch { $restoreErrors += ('Alert helper: ' + $_.ToString()) }
        try {
            [IO.File]::WriteAllBytes($mainPath, $mainOriginalBytes)
            if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($mainPath))) -ne $mainOriginalHash) { throw 'Restored main.dart did not pass verification.' }
        } catch { $restoreErrors += ('main.dart: ' + $_.ToString()) }
        if ($restoreErrors.Count -gt 0) {
            throw "Update failed and an original file could not be restored. Restore both backups: $backupDirectory. Original error: $installError. Restore errors: $($restoreErrors -join '; ')"
        }
        throw "Update failed; both original files were restored. Backups: $backupDirectory. Original error: $installError"
    }

    Write-Host 'SeaPoint alert label update installed.'
    Write-Host ('Backups: ' + $backupDirectory)
    Write-Host 'Run flutter analyze, then click Run in Android Studio to load the update on your phone.'
} finally {
    if (Test-Path -LiteralPath $stageDirectory) { Remove-Item -LiteralPath $stageDirectory -Recurse -Force }
}
