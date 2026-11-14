# Exercise the installer with partial source fixtures made from public patch
# contexts. No private app source, Android SDK, Docker or Flutter is needed.
$ErrorActionPreference = 'Stop'
# Supply a deterministic health response. This test never calls a live service.
function Invoke-RestMethod { param($Uri, $TimeoutSec)
    return @{status='ready';service='seapoint-marine-routing';routing_build='seapoint-hosted-caribbean-v1';
        coastline_dataset='caribbean-osm-gshhg-20261114-v1';depth_checked=$false}
}
function Start-Sleep { param($Seconds) }
$tokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $PSScriptRoot '../online-routing-update.ps1'), [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | Out-String) }
Set-StrictMode -Version 2.0
$installerPath = Join-Path $PSScriptRoot '../online-routing-update.ps1'
$installerText = [IO.File]::ReadAllText($installerPath)
$prefix = $installerText.Substring(0, $installerText.IndexOf('function Get-SeaPointHash('))
. ([scriptblock]::Create($prefix))
$fixtureRoot = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-installer-' + [Guid]::NewGuid().ToString('N'))
$originalLocation = Get-Location
$null = [IO.Directory]::CreateDirectory($fixtureRoot)
try {
    foreach ($definition in $definitions) {
        if ($null -ne $definition.PSObject.Properties['payload']) { continue }
        $path = Join-Path $fixtureRoot $definition.path
        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))
        $fixture = ''
        if ($definition.path -eq 'pubspec.yaml') { $fixture = "name: seapoint`ndependencies:`n" }
        foreach ($patch in $definition.patches) { $fixture += $patch.old + "`n// fixture context boundary`n" }
        foreach ($marker in $definition.markers) {
            if (!$fixture.Contains([string]$marker)) { $fixture += "`n" + $marker + "`n" }
        }
        $fixture += "`n// fixture unrelated edits preserved`n"
        [IO.File]::WriteAllText($path, $fixture, $utf8)
    }
    [IO.File]::WriteAllText((Join-Path $fixtureRoot 'pubspec.yaml'), "name: seapoint`n", $utf8)
    Set-Location -LiteralPath $fixtureRoot
    & ([scriptblock]::Create($installerText))
    $hashes = @{}
    foreach ($definition in $definitions) {
        $path = Join-Path $fixtureRoot $definition.path
        if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw 'An installed file is missing.' }
        $hashes[$definition.path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        if ($null -ne $definition.PSObject.Properties['payload']) {
            if ($hashes[$definition.path].ToLowerInvariant() -ne $definition.sha256) { throw 'Helper checksum differs.' }
        } else {
            $content = [IO.File]::ReadAllText($path)
            foreach ($patch in $definition.patches) {
                if (!$content.Contains([string]$patch.new)) { throw 'A source patch was not applied.' }
            }
            if (!$content.Contains('// fixture unrelated edits preserved')) { throw 'Unrelated text was lost.' }
        }
    }
    & ([scriptblock]::Create($installerText))
    foreach ($definition in $definitions) {
        $path = Join-Path $fixtureRoot $definition.path
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $hashes[$definition.path]) {
            throw 'A repeat installation changed the project.'
        }
    }
    $backups = @(Get-ChildItem -LiteralPath (Join-Path $fixtureRoot '.seapoint-backups') -Directory)
    if ($backups.Count -ne 1) { throw 'Expected a single verified backup directory.' }
    Write-Host ('Synthetic installation, backup and repeat installation passed: PowerShell ' + $PSVersionTable.PSVersion)
} finally {
    Set-Location -LiteralPath $originalLocation.Path
    Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
}
