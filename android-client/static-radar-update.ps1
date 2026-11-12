# SeaPoint static radar update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$definitions = @($utf8.GetString([Convert]::FromBase64String('W3sicGF0aCI6ImxpYi9tYWluLmRhcnQiLCJiYWNrdXBfbmFtZSI6Im1haW4uZGFydC5iYWsiLCJtYXJrZXJzIjpbImltcG9ydCAncGFja2FnZTpmbHV0dGVyL21hdGVyaWFsLmRhcnQnOyIsImNsYXNzIF9TZWFQb2ludEhvbWVTdGF0ZSBleHRlbmRzIFN0YXRlPFNlYVBvaW50SG9tZT4iXSwicGF0Y2hlcyI6W3sibmFtZSI6Ik9wZW4gdGhlIHB1Ymxpc2hlZCByYWRhciBkaXJlY3RseSIsIm9sZCI6IlVyaS5wYXJzZSgnJF9iYWNrZW5kQmFzZVVybC9yYWRhcicpLnJlcGxhY2UoIiwibmV3IjoiVXJpLnBhcnNlKCdodHRwczovL2FqZWN2MjcuZ2l0aHViLmlvL3NlYXBvaW50LWJhY2tlbmQvJykucmVwbGFjZSgifV19XQ==')) | ConvertFrom-Json)

function Get-SeaPointHash([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-SeaPointOriginalOffset([int]$normalizedOffset, $crlfPositions) {
    $extra = 0
    foreach ($position in $crlfPositions) {
        if ($position -ge $normalizedOffset) { break }
        $extra++
    }
    return $normalizedOffset + $extra
}

function Get-SeaPointPatchedFile([byte[]]$bytes, $definition) {
    $body = $utf8.GetString($bytes)
    $bom = ''
    while ($body.Length -gt 0 -and $body[0] -eq [char]0xFEFF) {
        $bom += [char]0xFEFF
        $body = $body.Substring(1)
    }
    $normalized = $body.Replace("`r`n", "`n").Replace("`r", "`n")
    foreach ($marker in $definition.markers) {
        if ([regex]::Matches($normalized, [regex]::Escape([string]$marker)).Count -ne 1) {
            throw ($definition.path + ' is not the expected SeaPoint file. No files changed.')
        }
    }

    # Inspect every block before making any replacements. Some old blocks are a
    # prefix of the new block; a complete new match consumes only those old
    # matches inside it. A separate old copy or any duplicate remains invalid.
    $ranges = @()
    $resolvedRanges = @()
    foreach ($patch in $definition.patches) {
        if ([string]::IsNullOrEmpty($patch.old) -or [string]::IsNullOrEmpty($patch.new) -or $patch.old -eq $patch.new) {
            throw 'The static radar patch definition is invalid. No files changed.'
        }
        $oldMatches = [regex]::Matches($normalized, [regex]::Escape([string]$patch.old))
        $newMatches = [regex]::Matches($normalized, [regex]::Escape([string]$patch.new))
        $outsideOld = @()
        foreach ($oldMatch in $oldMatches) {
            $consumed = $false
            foreach ($newMatch in $newMatches) {
                if ($oldMatch.Index -ge $newMatch.Index -and
                    $oldMatch.Index + $oldMatch.Length -le $newMatch.Index + $newMatch.Length) {
                    $consumed = $true
                    break
                }
            }
            if (!$consumed) { $outsideOld += $oldMatch }
        }
        if ($outsideOld.Count -eq 1 -and $newMatches.Count -eq 0) {
            $match = $outsideOld[0]
            $ranges += [PSCustomObject]@{ Start = $match.Index; Length = $match.Length; New = [string]$patch.new; Name = [string]$patch.name }
            $resolvedRanges += [PSCustomObject]@{ Start = $match.Index; Length = $match.Length }
        } elseif ($outsideOld.Count -eq 0 -and $newMatches.Count -eq 1) {
            $resolvedRanges += [PSCustomObject]@{ Start = $newMatches[0].Index; Length = $newMatches[0].Length }
        } else {
            throw ($definition.path + ' contains a missing or ambiguous update block: ' + $patch.name + '. No files changed.')
        }
    }
    $previousEnd = -1
    foreach ($range in @($resolvedRanges | Sort-Object Start)) {
        if ($range.Start -lt $previousEnd) { throw ($definition.path + ' update blocks overlap. No files changed.') }
        $previousEnd = $range.Start + $range.Length
    }
    if ($ranges.Count -eq 0) { return ,$bytes }

    # Map normalized offsets back to the original bytes. Only patch spans are
    # rewritten; unpatched text, BOM and mixed line endings remain untouched.
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

# Verify the public site before changing the app's URL. A disabled or incomplete
# Pages deployment leaves the existing working app untouched.
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $healthUrl = 'https://ajecv27.github.io/seapoint-backend/health.json?check=' + [DateTime]::UtcNow.ToString('yyyyMMddHHmm')
    $health = (Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 20).Content | ConvertFrom-Json
    $now = [long]([DateTime]::UtcNow - [DateTime]'1970-01-01').TotalSeconds
    if ($health.app -ne 'SeaPoint Radar' -or $health.status -ne 'ready' -or
        $health.static_manifest_version -ne 1 -or $health.rolling_horizon_hours -ne 48 -or
        [long]$health.published_at -gt $now + 300 -or $now - [long]$health.published_at -gt 86400 -or
        [long]$health.available_until -lt $now + 48 * 3600) {
        throw 'The static radar publication is not ready with full 48-hour coverage.'
    }
} catch {
    throw ('The published radar site is not ready yet. Enable GitHub Pages with Source: GitHub Actions, then run Publish radar. No project files changed. Details: ' + $_.ToString())
}

$items = @()
foreach ($definition in $definitions) {
    $path = Join-Path $projectRoot $definition.path
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
        throw ($definition.path + ' is missing or is not a regular file. No files changed.')
    }
    $original = [IO.File]::ReadAllBytes($path)
    $payload = Get-SeaPointPatchedFile $original $definition
    $items += [PSCustomObject]@{
        Relative = [string]$definition.path
        Path = $path
        BackupName = [string]$definition.backup_name
        Original = $original
        OriginalHash = Get-SeaPointHash $original
        Payload = $payload
        PayloadHash = Get-SeaPointHash $payload
    }
}
if (@($items | Where-Object { $_.OriginalHash -ne $_.PayloadHash }).Count -eq 0) {
    Write-Host 'The SeaPoint static radar update is already installed. Stop the app and click Run in Android Studio to load it on your phone.'
    return
}
foreach ($item in $items) {
    if (!(Test-Path -LiteralPath $item.Path -PathType Leaf) -or
        (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash) {
        throw 'A SeaPoint file changed while the update was being prepared. No files changed.'
    }
}

$backupDirectory = Join-Path $projectRoot ('.seapoint-backups/static-radar-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($backupDirectory)
foreach ($item in $items) {
    $backupPath = Join-Path $backupDirectory $item.BackupName
    [IO.File]::WriteAllBytes($backupPath, $item.Original)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $item.OriginalHash) {
        throw "A static radar update backup did not pass verification. No project files changed. Backups: $backupDirectory"
    }
}
foreach ($item in $items) {
    if (!(Test-Path -LiteralPath $item.Path -PathType Leaf) -or
        (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash) {
        throw "A SeaPoint file changed before installation. No files changed. Backups: $backupDirectory"
    }
}

try {
    foreach ($item in $items) {
        if ($item.OriginalHash -eq $item.PayloadHash) { continue }
        # WRITE_STARTUP_TARGET
        [IO.File]::WriteAllBytes($item.Path, $item.Payload)
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.PayloadHash) {
            throw ('Installed ' + $item.Relative + ' did not pass verification.')
        }
    }
} catch {
    $installError = $_
    $restoreErrors = @()
    foreach ($item in $items) {
        try {
            [IO.File]::WriteAllBytes($item.Path, $item.Original)
            if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash) {
                throw 'Restored file did not pass verification.'
            }
        } catch { $restoreErrors += ($item.Relative + ': ' + $_.ToString()) }
    }
    if ($restoreErrors.Count -gt 0) {
        throw "Startup update failed and an original file could not be restored. Restore the backups: $backupDirectory. Original error: $installError. Restore errors: $($restoreErrors -join '; ')"
    }
    throw "Startup update failed; original files were restored. Backups: $backupDirectory. Original error: $installError"
}

Write-Host 'SeaPoint static radar update installed.'
Write-Host ('Backups: ' + $backupDirectory)
Write-Host 'Run flutter analyze, then stop the app and click Run in Android Studio to load the update on your phone.'
