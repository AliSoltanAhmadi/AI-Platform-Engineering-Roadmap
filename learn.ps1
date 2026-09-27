# Thin PowerShell launcher for the Python session orchestrator.
param(
    [string]$Command = "start",
    [string]$Level,
    [string]$Answer,
    [string]$StatePath,
    [ValidateSet("en", "fa")]
    [string]$Lang = "en",
    [switch]$NonInteractive
)

# Keep Persian text and Unicode symbols stable in Windows PowerShell and modern terminals.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = "1"

if ($Command -eq "--version") {
    Write-Host "learn 0.1.0 (AI Platform Learning Tool)"
    exit 0
}
if ($Command -eq "--help" -or $Command -eq "-h") {
    Write-Host "Usage: learn start [-Level 1] [-Answer '...'] [-Lang en|fa] [-NonInteractive]"
    Write-Host "  start   Start session (default)"
    Write-Host "  --version  Show version"
    Write-Host "  --help     Show help"
    exit 0
}

if ($Command -ne "start") {
    Write-Error "What happened? Unknown command: $Command`nWhy? Only the start command is supported.`nWhat should I do now? Run learn --help, then use learn start."
    Write-Host "Usage: learn start [-Level 1] [-Answer 'docker pull nginx'] [-NonInteractive]"
    exit 64
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Error "What happened? Python was not found.`nWhy? No python command is available on PATH.`nWhat should I do now? Install Python 3.11 or newer (for example: winget install -e --id Python.Python.3.12), then reopen PowerShell."
    exit 1
}

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^(\d+)\.(\d+)$') {
    Write-Error "What happened? Python could not be started.`nWhy? The python command did not return a valid version.`nWhat should I do now? Repair Python or add a working Python 3.11+ installation to PATH, then reopen PowerShell."
    exit 1
}

$pythonMajor = [int]$Matches[1]
$pythonMinor = [int]$Matches[2]
if ($pythonMajor -lt 3 -or ($pythonMajor -eq 3 -and $pythonMinor -lt 11)) {
    Write-Error "What happened? Python $pythonVersion is incompatible.`nWhy? This tool requires Python 3.11 or newer.`nWhat should I do now? Upgrade Python, then reopen PowerShell."
    exit 1
}

$base = $PSScriptRoot
$pythonArgs = @("$base\src\session.py", "start")

if ($PSBoundParameters.ContainsKey("Level")) {
    $pythonArgs += @("--level", $Level)
}
if ($PSBoundParameters.ContainsKey("Answer")) {
    $pythonArgs += @("--answer", $Answer)
}
if ($PSBoundParameters.ContainsKey("StatePath")) {
    $pythonArgs += @("--state-path", $StatePath)
}
$pythonArgs += @("--lang", $Lang)
if ($NonInteractive) {
    $pythonArgs += "--non-interactive"
}

& python @pythonArgs
exit $LASTEXITCODE
