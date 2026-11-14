# Read-only Docker inspection. Never reads environment variables or credentials.
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

Write-Host 'SeaPoint routing service check'
Write-Host 'This only lists possible containers and project folders. It changes nothing.'
try {
    $lines = Invoke-SeaPointDocker -arguments @('ps', '-a', '--format', '{{json .}}')
    $found = $false
    foreach ($line in ($lines -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $container = $line | ConvertFrom-Json
        if (($container.Names + ' ' + $container.Ports + ' ' + $container.Image) -notmatch '(?i)route|routing|seapoint|8080|8083') { continue }
        $found = $true
        Write-Host ('Possible routing container: ' + $container.Names)
        Write-Host ('Ports: ' + $container.Ports)
        # Only the container's mount paths and Compose project-folder label are
        # requested, not its configuration/environment or any source contents.
        $format = '{"mounts":{{json .Mounts}},"folder":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}}}'
        $details = (Invoke-SeaPointDocker -arguments @('inspect', '--format', $format, $container.ID)) | ConvertFrom-Json
        if (![string]::IsNullOrWhiteSpace([string]$details.folder)) {
            Write-Host ('Project folder: ' + $details.folder)
        }
        foreach ($mount in @($details.mounts)) {
            if ($null -ne $mount -and $mount.Type -eq 'bind') {
                Write-Host ('Local folder: ' + $mount.Source + ' -> ' + $mount.Destination)
            }
        }
    }
    if (!$found) { Write-Host 'No matching container found. The separate routing project is not in the uploaded SeaPoint ZIP.' }
    Write-Host 'Copy this routing-check output into our chat so we can locate the existing server.'
} catch {
    Write-Host $_.Exception.Message
    Write-Host 'The trip-recovery update does not depend on Docker.'
}
