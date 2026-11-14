# Collect selected source files from existing SeaPoint routing containers.
# Does not start/stop containers, run container commands, or upload anything.
param(
    [string[]]$ContainerName = @('seapoint-clearance-test','seapoint-global-osm-test','seapoint-global-test','seapoint-routing'),
    [string]$OutputDirectory = (Get-Location).ProviderPath,
    [switch]$SkipLocalSchema
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

function Invoke-SeaPointDocker([string[]]$arguments) {
    $commands = @(Get-Command docker -CommandType Application -ErrorAction SilentlyContinue)
    if ($commands.Count -eq 0) { throw 'Docker command was not found. Open Docker Desktop first.' }
    $docker = $commands[0]
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $docker.Source
    # Every argument is generated here; no shell or user-provided commands run.
    $start.Arguments = (($arguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }) -join ' ')
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (!$process.WaitForExit(10000)) {
            $process.Kill()
            throw 'Docker did not respond. Open Docker Desktop and try again.'
        }
        if ($process.ExitCode -ne 0) { throw 'Docker is unavailable. Open Docker Desktop and try again.' }
        return $stdout.GetAwaiter().GetResult()
    } finally { $process.Dispose() }
}

function Copy-SeaPointSource([string]$name, [string]$sourcePath, [string]$targetPath) {
    try {
        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($targetPath))
        $null = Invoke-SeaPointDocker -arguments @('cp', ($name + ':' + $sourcePath), $targetPath)
        if (!(Test-Path -LiteralPath $targetPath -PathType Leaf)) { return $false }
        $size = (Get-Item -LiteralPath $targetPath).Length
        if ($size -gt 1048576 -or $script:seaPointSourceBytes + $size -gt 20971520) {
            [IO.File]::Delete($targetPath)
            return $false
        }
        $script:seaPointSourceBytes += $size
        return $true
    } catch { return $false }
}

function Join-SeaPointContainerPath([string]$root, [string]$relative) {
    return $root.TrimEnd('/') + '/' + $relative.TrimStart('/')
}

function Get-SeaPointImports([string]$source) {
    $modules = New-Object 'System.Collections.Generic.List[string]'
    foreach ($match in [regex]::Matches($source, '(?m)^\s*(?:from\s+([.\w]+)\s+import|import\s+([\w.]+))')) {
        $module = $match.Groups[1].Value
        if ($module.Length -eq 0) { $module = $match.Groups[2].Value }
        $module = $module.TrimStart('.')
        if ($module -match '^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$') { $modules.Add($module) }
    }
    return $modules.ToArray()
}

if (!(Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
    throw 'The export destination folder does not exist.'
}
$stage = Join-Path ([IO.Path]::GetTempPath()) ('seapoint-routing-export-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stage)
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$reports = New-Object 'System.Collections.Generic.List[object]'
$sourceCount = 0
$script:seaPointSourceBytes = 0
$skipImports = @('os','sys','math','re','json','time','datetime','pathlib','typing','dataclasses','collections',
    'heapq','functools','itertools','concurrent','threading','logging','random','statistics','enum','io','copy',
    'fastapi','uvicorn','pydantic','numpy','shapely','pyproj','geopandas','scipy','requests','httpx','starlette',
    'fiona','pyogrio','networkx','rasterio','affine','pandas','contextlib','urllib','struct','pickle','gzip')
try {
    foreach ($name in $ContainerName) {
        if ($name -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]*$') { throw 'Invalid routing container name.' }
        Write-Host ('Collecting routing source: ' + $name)
        $format = '{"workdir":{{json .Config.WorkingDir}},"cmd":{{json .Config.Cmd}},"entrypoint":{{json .Config.Entrypoint}},"image":{{json .Config.Image}},"mounts":{{json .Mounts}},"ports":{{json .NetworkSettings.Ports}}}'
        try {
            $metadataJson = Invoke-SeaPointDocker -arguments @('inspect', '--format', $format, $name)
            $metadata = ConvertFrom-Json -InputObject $metadataJson
        } catch {
            $reports.Add([PSCustomObject]@{ container = $name; status = 'unavailable' })
            continue
        }
        $roots = New-Object 'System.Collections.Generic.List[string]'
        $working = [string]$metadata.workdir
        if ($working.StartsWith('/')) { $roots.Add($working) }
        foreach ($root in @('/app','/code','/usr/src/app','/srv/app','/srv','/')) {
            if (!$roots.Contains($root)) { $roots.Add($root) }
        }
        $candidates = New-Object 'System.Collections.Generic.List[string]'
        # Read launch arguments only to identify Python filenames. Never save
        # the command, environment, credentials or a complete Docker inspect.
        foreach ($argument in (@($metadata.cmd) + @($metadata.entrypoint))) {
            foreach ($match in [regex]::Matches([string]$argument, '\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*):(?:app|application)\b')) {
                $relative = $match.Groups[1].Value.Replace('.', '/') + '.py'
                if (!$candidates.Contains($relative)) { $candidates.Add($relative) }
            }
            if ([string]$argument -match '^(?:\./)?([A-Za-z_]\w*(?:/[A-Za-z_]\w*)*\.py)$') {
                if (!$candidates.Contains($Matches[1])) { $candidates.Add($Matches[1]) }
            }
        }
        foreach ($candidate in @('server.py','main.py','app.py','app/main.py','app/server.py')) {
            if (!$candidates.Contains($candidate)) { $candidates.Add($candidate) }
        }
        $folder = Join-Path $stage $name
        $null = [IO.Directory]::CreateDirectory($folder)
        $entry = $null
        $codeRoot = $null
        foreach ($root in $roots) {
            foreach ($candidate in $candidates) {
                $destination = Join-Path $folder $candidate
                if (Copy-SeaPointSource $name (Join-SeaPointContainerPath $root $candidate) $destination) {
                    $entry = $candidate
                    $codeRoot = $root
                    break
                }
            }
            if ($null -ne $entry) { break }
        }
        if ($null -eq $entry) {
            $reports.Add([PSCustomObject]@{ container = $name; status = 'source_not_found'; working_directory = $working })
            continue
        }
        $copied = New-Object 'System.Collections.Generic.List[string]'
        $copied.Add($entry)
        $checked = New-Object 'System.Collections.Generic.HashSet[string]'
        $null = $checked.Add($entry)
        # Collect local helper modules referenced by the entry point, bounded
        # to app-relative Python paths. No directory copies or package caches.
        for ($index = 0; $index -lt $copied.Count -and $copied.Count -lt 25; $index++) {
            $relative = $copied[$index]
            $source = [IO.File]::ReadAllText((Join-Path $folder $relative))
            $slash = $relative.LastIndexOf('/')
            $parent = ''
            if ($slash -ge 0) { $parent = $relative.Substring(0, $slash + 1) }
            foreach ($module in @(Get-SeaPointImports $source)) {
                if ($skipImports -contains $module.Split('.')[0]) { continue }
                $modulePath = $module.Replace('.', '/')
                foreach ($possible in @(($modulePath + '.py'), ($modulePath + '/__init__.py'), ($parent + $modulePath + '.py'))) {
                    if ($copied.Count -ge 25) { break }
                    if (!$checked.Add($possible)) { continue }
                    if (Copy-SeaPointSource $name (Join-SeaPointContainerPath $codeRoot $possible) (Join-Path $folder $possible)) {
                        $copied.Add($possible)
                    }
                }
            }
        }
        foreach ($extra in @('requirements.txt','requirements-routing.txt','pyproject.toml','Dockerfile')) {
            $null = Copy-SeaPointSource $name (Join-SeaPointContainerPath $codeRoot $extra) (Join-Path $folder $extra)
        }
        $datasets = New-Object 'System.Collections.Generic.List[object]'
        foreach ($mount in @($metadata.mounts)) {
            if ($null -eq $mount -or $mount.Type -ne 'bind' -or
                [string]$mount.Destination -notmatch '(?i)coast|land|data') { continue }
            $files = @()
            try {
                $files = @(Get-ChildItem -LiteralPath $mount.Source -File -ErrorAction Stop |
                    Sort-Object Name | Select-Object -First 40 Name, Length)
            } catch {}
            $datasets.Add([PSCustomObject]@{ container_path = $mount.Destination; files = $files })
        }
        # Optional local API schema is a read-only request, with no coordinates
        # or API key. Only the container's published 8080 port is considered.
        if (!$SkipLocalSchema -and $null -ne $metadata.ports -and
            $null -ne $metadata.ports.PSObject.Properties['8080/tcp']) {
            $bindings = @($metadata.ports.PSObject.Properties['8080/tcp'].Value)
            if ($bindings.Count -gt 0) {
                $port = [string]$bindings[0].HostPort
                if ($port -match '^\d{2,5}$' -and [int]$port -le 65535) {
                    try {
                        $schema = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri ('http://127.0.0.1:' + $port + '/openapi.json')).Content
                        if ($schema.Length -le 1048576) {
                            $parsedSchema = ConvertFrom-Json -InputObject $schema
                            if ($null -ne $parsedSchema.PSObject.Properties['openapi']) {
                                [IO.File]::WriteAllText((Join-Path $folder 'openapi.json'), $schema, $utf8)
                            }
                        }
                    } catch {}
                }
            }
        }
        $sourceCount += $copied.Count
        $reports.Add([PSCustomObject]@{ container = $name; status = 'collected';
            image = $metadata.image; working_directory = $working; code_root = $codeRoot;
            entry_file = $entry; python_files = $copied.ToArray(); coastline = $datasets.ToArray() })
        Write-Host ('  Python source files: ' + $copied.Count)
    }
    if ($sourceCount -eq 0) { throw 'No routing source could be collected. Keep Docker Desktop running and send the messages above.' }
    $reportJson = ConvertTo-Json -InputObject ($reports.ToArray()) -Depth 8
    [IO.File]::WriteAllText((Join-Path $stage 'routing-export.json'), $reportJson, $utf8)
    $readme = 'Local SeaPoint routing source for private review. No containers or app files were changed. ' +
        'The archive contains selected Python/build files and optional API schemas. ' +
        'No .env files, Docker environment variables, credentials files or coastline geometry were collected.'
    [IO.File]::WriteAllText((Join-Path $stage 'README.txt'), $readme, $utf8)
    $archive = Join-Path $OutputDirectory ('SeaPoint-Routing-Code-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6) + '.zip')
    Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $archive -CompressionLevel Optimal
    Write-Host ''
    Write-Host ('Created: ' + $archive)
    Write-Host 'Attach this ZIP in our SeaPoint chat so the routing code can be reviewed.'
} finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
