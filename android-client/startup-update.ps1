# SeaPoint startup update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$definitions = @($utf8.GetString([Convert]::FromBase64String('W3sicGF0aCI6ImxpYi9tYWluLmRhcnQiLCJiYWNrdXBfbmFtZSI6Im1haW4uZGFydC5iYWsiLCJtYXJrZXJzIjpbImltcG9ydCAncGFja2FnZTpmbHV0dGVyL21hdGVyaWFsLmRhcnQnOyIsImltcG9ydCAnbmF2aWdhdGlvbl9zY3JlZW4uZGFydCc7IiwiY2xhc3MgU2VhUG9pbnRBcHAgZXh0ZW5kcyBTdGF0ZWxlc3NXaWRnZXQiLCJjbGFzcyBfU2VhUG9pbnRIb21lU3RhdGUgZXh0ZW5kcyBTdGF0ZTxTZWFQb2ludEhvbWU+Il0sInBhdGNoZXMiOlt7Im5hbWUiOiJkZWZlci1uYXZpZ2F0aW9uLXVudGlsLW9wZW5lZCIsIm9sZCI6ImNsYXNzIF9TZWFQb2ludEhvbWVTdGF0ZSBleHRlbmRzIFN0YXRlPFNlYVBvaW50SG9tZT4ge1xuICBpbnQgX3NlbGVjdGVkSW5kZXggPSAwOyIsIm5ldyI6ImNsYXNzIF9TZWFQb2ludEhvbWVTdGF0ZSBleHRlbmRzIFN0YXRlPFNlYVBvaW50SG9tZT4ge1xuICBpbnQgX3NlbGVjdGVkSW5kZXggPSAwO1xuICBib29sIF9uYXZpZ2F0aW9uT3BlbmVkID0gZmFsc2U7In0seyJuYW1lIjoia2VlcC11bm9wZW5lZC1uYXZpZ2F0aW9uLWxpZ2h0d2VpZ2h0Iiwib2xkIjoiICAgICAgICBjaGlsZHJlbjogY29uc3QgW1xuICAgICAgICAgIE1hcmluZURhc2hib2FyZCgpLFxuICAgICAgICAgIE5hdmlnYXRpb25TY3JlZW4oKSxcbiAgICAgICAgXSwiLCJuZXciOiIgICAgICAgIGNoaWxkcmVuOiBbXG4gICAgICAgICAgY29uc3QgTWFyaW5lRGFzaGJvYXJkKCksXG4gICAgICAgICAgX25hdmlnYXRpb25PcGVuZWRcbiAgICAgICAgICAgICAgPyBjb25zdCBOYXZpZ2F0aW9uU2NyZWVuKClcbiAgICAgICAgICAgICAgOiBjb25zdCBTaXplZEJveC5zaHJpbmsoKSxcbiAgICAgICAgXSwifSx7Im5hbWUiOiJyZXRhaW4tbmF2aWdhdGlvbi1hZnRlci1maXJzdC1zZWxlY3Rpb24iLCJvbGQiOiIgICAgICAgIG9uRGVzdGluYXRpb25TZWxlY3RlZDogKGluZGV4KSB7XG4gICAgICAgICAgc2V0U3RhdGUoKCkge1xuICAgICAgICAgICAgX3NlbGVjdGVkSW5kZXggPSBpbmRleDtcbiAgICAgICAgICB9KTtcbiAgICAgICAgfSwiLCJuZXciOiIgICAgICAgIG9uRGVzdGluYXRpb25TZWxlY3RlZDogKGluZGV4KSB7XG4gICAgICAgICAgc2V0U3RhdGUoKCkge1xuICAgICAgICAgICAgX3NlbGVjdGVkSW5kZXggPSBpbmRleDtcbiAgICAgICAgICAgIGlmIChpbmRleCA9PSAxKSB7XG4gICAgICAgICAgICAgIF9uYXZpZ2F0aW9uT3BlbmVkID0gdHJ1ZTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9KTtcbiAgICAgICAgfSwifV19LHsicGF0aCI6ImxpYi9yYWRhcl9zY3JlZW4uZGFydCIsImJhY2t1cF9uYW1lIjoicmFkYXJfc2NyZWVuLmRhcnQuYmFrIiwibWFya2VycyI6WyJpbXBvcnQgJ3BhY2thZ2U6d2Vidmlld19mbHV0dGVyL3dlYnZpZXdfZmx1dHRlci5kYXJ0JzsiLCJjbGFzcyBSYWRhclNjcmVlbiBleHRlbmRzIFN0YXRlZnVsV2lkZ2V0IiwiY2xhc3MgX1JhZGFyU2NyZWVuU3RhdGUgZXh0ZW5kcyBTdGF0ZTxSYWRhclNjcmVlbj4iLCInU2VhUG9pbnRSYWRhciciXSwicGF0Y2hlcyI6W3sibmFtZSI6InJhZGFyLWxvYWQtd2F0Y2hkb2ctZmllbGQiLCJvbGQiOiIgIFRpbWVyPyBfcmV0cnlUaW1lcjsiLCJuZXciOiIgIFRpbWVyPyBfcmV0cnlUaW1lcjtcbiAgVGltZXI/IF9sb2FkV2F0Y2hkb2c7In0seyJuYW1lIjoiY2FuY2VsLXdhdGNoZG9nLW9uLXJlYWR5Iiwib2xkIjoiICAgICAgICAgICAgX3JldHJ5VGltZXI/LmNhbmNlbCgpO1xuXG4gICAgICAgICAgICBzZXRTdGF0ZSgoKSB7XG4gICAgICAgICAgICAgIF9yZWFkeSA9IHRydWU7IiwibmV3IjoiICAgICAgICAgICAgX3JldHJ5VGltZXI/LmNhbmNlbCgpO1xuICAgICAgICAgICAgX2xvYWRXYXRjaGRvZz8uY2FuY2VsKCk7XG5cbiAgICAgICAgICAgIHNldFN0YXRlKCgpIHtcbiAgICAgICAgICAgICAgX3JlYWR5ID0gdHJ1ZTsifSx7Im5hbWUiOiJ0ZXN0LW1hcC1ib290LXN0YXRlIiwib2xkIjoiICAgICAgICAgICAgICAgIFwiQm9vbGVhbihkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbWFwJykpXCIsIiwibmV3IjoiICAgICAgICAgICAgICAgIFwiQm9vbGVhbih3aW5kb3cuc2VhcG9pbnRCb290UmVhZHkgfHwgd2luZG93LnNlYXBvaW50TW90aW9uU3RhdGUpXCIsIn0seyJuYW1lIjoicmVjb3Zlci1taXNzZWQtcmVhZHktYnJpZGdlIiwib2xkIjoiICAgICAgICAgICAgICBpZiAocmVzdWx0LnRvU3RyaW5nKCkgIT0gJ3RydWUnKSB7XG4gICAgICAgICAgICAgICAgX3NjaGVkdWxlUmVsb2FkKCk7XG4gICAgICAgICAgICAgIH0iLCJuZXciOiIgICAgICAgICAgICAgIGlmIChyZXN1bHQudG9TdHJpbmcoKSA9PSAndHJ1ZScpIHtcbiAgICAgICAgICAgICAgICBhd2FpdCBfd2ViVmlldy5ydW5KYXZhU2NyaXB0KFxuICAgICAgICAgICAgICAgICAgXCJ3aW5kb3cuU2VhUG9pbnRSYWRhciAmJiB3aW5kb3cuU2VhUG9pbnRSYWRhci5wb3N0TWVzc2FnZSgncmVhZHknKTtcIixcbiAgICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIF9zY2hlZHVsZVJlbG9hZCgpO1xuICAgICAgICAgICAgICB9In0seyJuYW1lIjoiYXJtLWluaXRpYWwtcmFkYXItd2F0Y2hkb2ciLCJvbGQiOiIgICAgICAuLmxvYWRSZXF1ZXN0KHdpZGdldC51cmkpO1xuICB9XG5cbiAgdm9pZCBfc2NoZWR1bGVSZWxvYWQoKSB7IiwibmV3IjoiICAgICAgLi5sb2FkUmVxdWVzdCh3aWRnZXQudXJpKTtcbiAgICBfc3RhcnRMb2FkV2F0Y2hkb2coKTtcbiAgfVxuXG4gIHZvaWQgX3N0YXJ0TG9hZFdhdGNoZG9nKCkge1xuICAgIF9sb2FkV2F0Y2hkb2c/LmNhbmNlbCgpO1xuICAgIGlmICghbW91bnRlZCB8fCBfcmVhZHkpIHJldHVybjtcbiAgICBfbG9hZFdhdGNoZG9nID0gVGltZXIoY29uc3QgRHVyYXRpb24oc2Vjb25kczogMzApLCAoKSB7XG4gICAgICBpZiAoIW1vdW50ZWQgfHwgX3JlYWR5KSByZXR1cm47XG4gICAgICBzZXRTdGF0ZSgoKSB7XG4gICAgICAgIF9mYWlsZWQgPSB0cnVlO1xuICAgICAgfSk7XG4gICAgfSk7XG4gIH1cblxuICB2b2lkIF9zY2hlZHVsZVJlbG9hZCgpIHsifSx7Im5hbWUiOiJyZWFybS13YXRjaGRvZy1vbi11c2VyLXJldHJ5Iiwib2xkIjoiICAgICAgX2ZhaWxlZCA9IGZhbHNlO1xuICAgICAgX3JlYWR5ID0gZmFsc2U7XG4gICAgfSk7XG5cbiAgICBfd2ViVmlldy5yZWxvYWQoKTtcbiAgfVxuXG4gIEBvdmVycmlkZVxuICB2b2lkIGRpc3Bvc2UoKSB7IiwibmV3IjoiICAgICAgX2ZhaWxlZCA9IGZhbHNlO1xuICAgICAgX3JlYWR5ID0gZmFsc2U7XG4gICAgfSk7XG5cbiAgICBfc3RhcnRMb2FkV2F0Y2hkb2coKTtcbiAgICBfd2ViVmlldy5yZWxvYWQoKTtcbiAgfVxuXG4gIEBvdmVycmlkZVxuICB2b2lkIGRpc3Bvc2UoKSB7In0seyJuYW1lIjoiZGlzcG9zZS1yYWRhci13YXRjaGRvZyIsIm9sZCI6IiAgICBfcmV0cnlUaW1lcj8uY2FuY2VsKCk7XG4gICAgc3VwZXIuZGlzcG9zZSgpOyIsIm5ldyI6IiAgICBfcmV0cnlUaW1lcj8uY2FuY2VsKCk7XG4gICAgX2xvYWRXYXRjaGRvZz8uY2FuY2VsKCk7XG4gICAgc3VwZXIuZGlzcG9zZSgpOyJ9LHsibmFtZSI6ImV4cGxhaW4tc2xvdy1yYWRhci13aXRob3V0LWZhbHNlLXVuYXZhaWxhYmxlIiwib2xkIjoiJ1JhZGFyIGlzIHRlbXBvcmFyaWx5IHVuYXZhaWxhYmxlJyIsIm5ldyI6IidSYWRhciBpcyB0YWtpbmcgbG9uZ2VyIHRvIGxvYWQnIn1dfV0=')) | ConvertFrom-Json)

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
            throw 'The startup patch definition is invalid. No files changed.'
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
    Write-Host 'The SeaPoint startup update is already installed. Stop the app and click Run in Android Studio to load it on your phone.'
    return
}
foreach ($item in $items) {
    if (!(Test-Path -LiteralPath $item.Path -PathType Leaf) -or
        (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash) {
        throw 'A SeaPoint file changed while the update was being prepared. No files changed.'
    }
}

$backupDirectory = Join-Path $projectRoot ('.seapoint-backups/startup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($backupDirectory)
foreach ($item in $items) {
    $backupPath = Join-Path $backupDirectory $item.BackupName
    [IO.File]::WriteAllBytes($backupPath, $item.Original)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $item.OriginalHash) {
        throw "A startup update backup did not pass verification. No project files changed. Backups: $backupDirectory"
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
        throw "Startup update failed and an original file could not be restored. Restore both backups: $backupDirectory. Original error: $installError. Restore errors: $($restoreErrors -join '; ')"
    }
    throw "Startup update failed; both original files were restored. Backups: $backupDirectory. Original error: $installError"
}

Write-Host 'SeaPoint startup update installed.'
Write-Host ('Backups: ' + $backupDirectory)
Write-Host 'Run flutter analyze, then stop the app and click Run in Android Studio to load the update on your phone.'
