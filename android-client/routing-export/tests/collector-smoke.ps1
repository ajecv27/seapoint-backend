# Read-only Docker calls are simulated; no real containers or private code used.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$collector = Join-Path $PSScriptRoot '../../export-routing-code.ps1'
$text = [IO.File]::ReadAllText($collector)
$tokens = $null
$errors = $null
$tree = [System.Management.Automation.Language.Parser]::ParseFile($collector, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw ($errors | Out-String) }
$function = $tree.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Invoke-SeaPointDocker'}, $true)
if ($null -eq $function) { throw 'Docker helper not found.' }
$fake = @'
function Invoke-SeaPointDocker([string[]]$arguments) {
    $script:calls.Add(($arguments -join ' '))
    if ($arguments[0] -eq 'inspect') {
        if ($arguments[2].Contains('.Config.Env')) { throw 'Environment variables must not be inspected.' }
        $name = $arguments[3]
        if ($name -eq 'missing-container') { throw 'Container missing' }
        $root = '/code'
        $module = 'server:app'
        if ($name -eq 'package-container') { $root = '/srv/app'; $module = 'routing.main:app' }
        return ConvertTo-Json -InputObject @{workdir=$root;cmd=@('uvicorn',$module,'--secret-do-not-export=EXAMPLE');entrypoint=$null;
            image='seapoint-local-routing';mounts=@(@{Type='bind';Source=$script:coast;Destination='/coast'});ports=@{}} -Depth 6
    }
    if ($arguments[0] -ne 'cp') { throw 'Only inspect and cp calls are allowed.' }
    $colon = $arguments[1].IndexOf(':')
    $name = $arguments[1].Substring(0,$colon)
    $path = $arguments[1].Substring($colon+1)
    $files = @{
        '/code/server.py' = "from fastapi import FastAPI`nfrom helpers import water_route`nimport large_helper`napp=FastAPI()`n@app.get('/route')`ndef route(start_lat:float,end_lat:float): return water_route()`n"
        '/code/helpers.py' = "import math`ndef water_route(): return 'test only'`n"
        '/code/large_helper.py' = ('x' * 1048577)
        '/code/requirements.txt' = "fastapi`nshapely`npyproj`n"
        '/srv/app/routing/main.py' = "from .helpers import water_route`nfrom fastapi import FastAPI`napp=FastAPI()`n"
        '/srv/app/routing/helpers.py' = "def water_route(): return 'package test'`n"
        '/srv/app/requirements.txt' = 'fastapi'
    }
    if (!$files.ContainsKey($path)) { throw 'Source file does not exist' }
    $value = [string]$files[$path]
    [IO.File]::WriteAllText($arguments[2],$value)
    return ''
}
'@
$modified = $text.Substring(0,$function.Extent.StartOffset)+$fake+$text.Substring($function.Extent.EndOffset)
$script:calls = New-Object 'System.Collections.Generic.List[string]'
$root = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-export-test-'+[Guid]::NewGuid().ToString('N'))
$script:coast = Join-Path $root 'coast'
$output = Join-Path $root 'output'
$null = [IO.Directory]::CreateDirectory($script:coast)
$null = [IO.Directory]::CreateDirectory($output)
[IO.File]::WriteAllText((Join-Path $script:coast 'land_polygons.shp'),'geometry must stay local')
[IO.File]::WriteAllText((Join-Path $script:coast '.env'),'credentials must stay local')
try {
    & ([scriptblock]::Create($modified)) -ContainerName @('server-container','package-container','missing-container') -OutputDirectory $output -SkipLocalSchema
    $archives = @(Get-ChildItem -LiteralPath $output -Filter '*.zip' -File)
    if ($archives.Count -ne 1) { throw 'Expected one source archive.' }
    $expanded = Join-Path $root 'expanded'
    Expand-Archive -LiteralPath $archives[0].FullName -DestinationPath $expanded
    foreach ($relative in @('server-container/server.py','server-container/helpers.py','server-container/requirements.txt',
        'package-container/routing/main.py','package-container/routing/helpers.py','routing-export.json')) {
        if (!(Test-Path -LiteralPath (Join-Path $expanded $relative) -PathType Leaf)) { throw ('Missing collected file: '+$relative) }
    }
    if (@(Get-ChildItem -LiteralPath $expanded -Recurse -File | Where-Object { $_.Name -eq '.env' -or $_.Extension -eq '.shp' }).Count -ne 0) {
        throw 'Coastline or credential file was copied.'
    }
    if (Test-Path -LiteralPath (Join-Path $expanded 'server-container/large_helper.py')) { throw 'Oversized source was not excluded.' }
    $report = [IO.File]::ReadAllText((Join-Path $expanded 'routing-export.json'))
    if ($report.Contains('EXAMPLE') -or $report.Contains('secret-do-not-export')) { throw 'Launch arguments leaked into report.' }
    if (!$report.Contains('land_polygons.shp')) { throw 'Coastline filenames should be described without copying geometry.' }
    if (@($script:calls | Where-Object { $_ -notmatch '^(inspect|cp) ' }).Count -ne 0) { throw 'A container was changed or executed.' }
    # Repeating the collector must preserve the earlier bundle.
    & ([scriptblock]::Create($modified)) -ContainerName @('server-container') -OutputDirectory $output -SkipLocalSchema
    if (@(Get-ChildItem -LiteralPath $output -Filter '*.zip' -File).Count -ne 2) { throw 'An existing archive was overwritten.' }
    Write-Host ('Routing export source/modules/metadata/archive checks passed: PowerShell '+$PSVersionTable.PSVersion)
} finally {
    Remove-Item -LiteralPath $root -Recurse -Force
}
