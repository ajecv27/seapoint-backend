# Parsing regression only: no project files, network, Docker or Flutter needed.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$installer = Join-Path $PSScriptRoot '../../trip-recovery-update.ps1'
$text = [IO.File]::ReadAllText($installer)
$index = $text.IndexOf('function Get-SeaPointHash(')
if ($index -lt 1) { throw 'Installer parser was not found.' }
$prefix = $text.Substring(0, $index)
$checks = @'
if ($definitions.Count -ne 9) { throw 'Expected nine separate file definitions.' }
foreach ($definition in $definitions) {
    if ($definition -is [array] -or $definition.path -isnot [string]) {
        throw 'A nested JSON array reached the file loop.'
    }
}
'@

& ([scriptblock]::Create($prefix + $checks))
Write-Host 'Native JSON parsing: nine scalar file paths.'

if ($PSVersionTable.PSVersion.Major -ge 7) {
    # PowerShell 7 added enumeration by default. Reproduce 5.1's top-level
    # array output using the native cmdlet's explicit NoEnumerate option.
    function ConvertFrom-Json {
        [CmdletBinding()]
        param([Parameter(ValueFromPipeline=$true, Mandatory=$true)][object]$InputObject)
        process {
            $parsed = Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject $InputObject -NoEnumerate
            Write-Output -NoEnumerate $parsed
        }
    }
    & ([scriptblock]::Create($prefix + $checks))
    Write-Host 'PowerShell 5.1-style JSON output: nine scalar file paths.'
}
