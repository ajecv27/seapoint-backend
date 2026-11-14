# SeaPoint launch update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$definitions = @($utf8.GetString([Convert]::FromBase64String('W3sicGF0aCI6ImxpYi9tYWluLmRhcnQiLCJiYWNrdXBfbmFtZSI6Im1haW4uZGFydC5iYWsiLCJtYXJrZXJzIjpbImltcG9ydCAncGFja2FnZTpmbHV0dGVyL21hdGVyaWFsLmRhcnQnOyIsImNsYXNzIF9TZWFQb2ludEhvbWVTdGF0ZSBleHRlbmRzIFN0YXRlPFNlYVBvaW50SG9tZT4iXSwicGF0Y2hlcyI6W3sibmFtZSI6ImRlZmVyLW5hdmlnYXRpb24tdW50aWwtb3BlbmVkIiwib2xkIjoiY2xhc3MgX1NlYVBvaW50SG9tZVN0YXRlIGV4dGVuZHMgU3RhdGU8U2VhUG9pbnRIb21lPiB7XG4gIGludCBfc2VsZWN0ZWRJbmRleCA9IDA7IiwibmV3IjoiY2xhc3MgX1NlYVBvaW50SG9tZVN0YXRlIGV4dGVuZHMgU3RhdGU8U2VhUG9pbnRIb21lPiB7XG4gIGludCBfc2VsZWN0ZWRJbmRleCA9IDA7XG4gIGJvb2wgX25hdmlnYXRpb25PcGVuZWQgPSBmYWxzZTsifSx7Im5hbWUiOiJrZWVwLXVub3BlbmVkLW5hdmlnYXRpb24tbGlnaHR3ZWlnaHQiLCJvbGQiOiIgICAgICAgIGNoaWxkcmVuOiBjb25zdCBbXG4gICAgICAgICAgTWFyaW5lRGFzaGJvYXJkKCksXG4gICAgICAgICAgTmF2aWdhdGlvblNjcmVlbigpLFxuICAgICAgICBdLCIsIm5ldyI6IiAgICAgICAgY2hpbGRyZW46IFtcbiAgICAgICAgICBjb25zdCBNYXJpbmVEYXNoYm9hcmQoKSxcbiAgICAgICAgICBfbmF2aWdhdGlvbk9wZW5lZFxuICAgICAgICAgICAgICA/IGNvbnN0IE5hdmlnYXRpb25TY3JlZW4oKVxuICAgICAgICAgICAgICA6IGNvbnN0IFNpemVkQm94LnNocmluaygpLFxuICAgICAgICBdLCJ9LHsibmFtZSI6InJldGFpbi1uYXZpZ2F0aW9uLWFmdGVyLWZpcnN0LXNlbGVjdGlvbiIsIm9sZCI6IiAgICAgICAgb25EZXN0aW5hdGlvblNlbGVjdGVkOiAoaW5kZXgpIHtcbiAgICAgICAgICBzZXRTdGF0ZSgoKSB7XG4gICAgICAgICAgICBfc2VsZWN0ZWRJbmRleCA9IGluZGV4O1xuICAgICAgICAgIH0pO1xuICAgICAgICB9LCIsIm5ldyI6IiAgICAgICAgb25EZXN0aW5hdGlvblNlbGVjdGVkOiAoaW5kZXgpIHtcbiAgICAgICAgICBzZXRTdGF0ZSgoKSB7XG4gICAgICAgICAgICBfc2VsZWN0ZWRJbmRleCA9IGluZGV4O1xuICAgICAgICAgICAgaWYgKGluZGV4ID09IDEpIHtcbiAgICAgICAgICAgICAgX25hdmlnYXRpb25PcGVuZWQgPSB0cnVlO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH0pO1xuICAgICAgICB9LCJ9LHsibmFtZSI6InBhaW50LWJlZm9yZS1jYWNoZS1hbmQtcmVmcmVzaCIsIm9sZCI6IiAgICBfaW5pdGlhbGl6ZVdlYXRoZXIoKTtcblxuICAgIF9yZWZyZXNoVGltZXIgPSBUaW1lci5wZXJpb2RpYygiLCJuZXciOiIgICAgLy8gUGFpbnQgdGhlIGRhc2hib2FyZCBiZWZvcmUgc3RhcnRpbmcgcGxhdGZvcm0tY2FjaGUgd29yayBhbmQgcmVmcmVzaGVzLlxuICAgIFdpZGdldHNCaW5kaW5nLmluc3RhbmNlLmFkZFBvc3RGcmFtZUNhbGxiYWNrKChfKSB7XG4gICAgICBpZiAobW91bnRlZCkge1xuICAgICAgICB1bmF3YWl0ZWQoX2luaXRpYWxpemVXZWF0aGVyKCkpO1xuICAgICAgfVxuICAgIH0pO1xuXG4gICAgX3JlZnJlc2hUaW1lciA9IFRpbWVyLnBlcmlvZGljKCJ9LHsibmFtZSI6ImxvYWQtdXBkYXRlZC1yYWRhci1wYWdlIiwib2xkIjoiICAgICAgICAnbmFtZSc6IF9zZWxlY3RlZExvY2F0aW9uLm5hbWUsXG4gICAgICB9LFxuICAgICk7IiwibmV3IjoiICAgICAgICAnbmFtZSc6IF9zZWxlY3RlZExvY2F0aW9uLm5hbWUsXG4gICAgICAgICd1aSc6ICdoYW5kb3Zlci0yMDI2MTExNCcsXG4gICAgICB9LFxuICAgICk7In1dfV0=')) | ConvertFrom-Json)

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
            throw 'The launch patch definition is invalid. No files changed.'
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

# Release builds need the Internet permission in the main manifest. Preserve all
# existing permissions and XML formatting; do not serialize the user's document.
$manifestRelative = 'android/app/src/main/AndroidManifest.xml'
$manifestPath = Join-Path $projectRoot $manifestRelative
if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'AndroidManifest.xml is missing. Run this from the Android Studio project folder. No files changed.'
}
$manifestText = $utf8.GetString([IO.File]::ReadAllBytes($manifestPath)).Replace("`r`n", "`n").Replace("`r", "`n")
$xml = New-Object System.Xml.XmlDocument
$xml.XmlResolver = $null
$xml.LoadXml($manifestText.TrimStart([char]0xFEFF))
$androidNamespace = 'http://schemas.android.com/apk/res/android'
if ($xml.DocumentElement.LocalName -ne 'manifest' -or $xml.DocumentElement.GetNamespaceOfPrefix('android') -ne $androidNamespace) {
    throw 'Unexpected Android manifest format. No files changed.'
}
$openings = [regex]::Matches($manifestText, '<manifest\b[^>]*>')
if ($openings.Count -ne 1) { throw 'Ambiguous Android manifest. No files changed.' }
$opening = $openings[0].Value
$internet = @($xml.DocumentElement.ChildNodes | Where-Object {
    $_.LocalName -eq 'uses-permission' -and $_.GetAttribute('name', $androidNamespace) -eq 'android.permission.INTERNET'
})
$manifestPatches = @()
if ($internet.Count -eq 0) {
    $manifestPatches = @([PSCustomObject]@{
        name = 'Internet access in release builds'
        old = $opening
        new = $opening + "`n    <uses-permission android:name=`"android.permission.INTERNET`" />"
    })
}
$definitions += [PSCustomObject]@{
    path = $manifestRelative
    backup_name = 'AndroidManifest.xml.bak'
    markers = @($opening)
    patches = $manifestPatches
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
    Write-Host 'The SeaPoint launch update is already installed. Run flutter analyze, then flutter run --release with your phone connected.'
    return
}
foreach ($item in $items) {
    if (!(Test-Path -LiteralPath $item.Path -PathType Leaf) -or
        (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash) {
        throw 'A SeaPoint file changed while the update was being prepared. No files changed.'
    }
}

$backupDirectory = Join-Path $projectRoot ('.seapoint-backups/launch-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($backupDirectory)
foreach ($item in $items) {
    $backupPath = Join-Path $backupDirectory $item.BackupName
    [IO.File]::WriteAllBytes($backupPath, $item.Original)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $item.OriginalHash) {
        throw "A launch update backup did not pass verification. No project files changed. Backups: $backupDirectory"
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

Write-Host 'SeaPoint launch update installed.'
Write-Host ('Backups: ' + $backupDirectory)
Write-Host 'Run flutter analyze, then flutter run --release with your phone connected.'
