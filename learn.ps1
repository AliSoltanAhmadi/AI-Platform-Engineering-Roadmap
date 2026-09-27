# Thin PowerShell launcher for the Python session orchestrator.
param(
    [string]$Command = "start",
    [string]$Level,
    [string]$Answer,
    [string]$StatePath,
    [switch]$NonInteractive
)

if ($Command -eq "--version") {
    Write-Host "learn 0.1.0 (AI Platform Learning Tool)"
    exit 0
}
if ($Command -eq "--help" -or $Command -eq "-h") {
    Write-Host "Usage: learn start [-Level 1] [-Answer '...'] [-NonInteractive]"
    Write-Host "  start   Start session (default)"
    Write-Host "  --version  Show version"
    Write-Host "  --help     Show help"
    exit 0
}

if ($Command -ne "start") {
    Write-Error "Unknown command: $Command"
    Write-Host "Usage: learn start [-Level 1] [-Answer 'docker pull nginx'] [-NonInteractive]"
    exit 64
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Error "Python was not found. Install Python 3.11 or newer (for example: winget install -e --id Python.Python.3.12), then reopen PowerShell."
    exit 1
}

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^(\d+)\.(\d+)$') {
    Write-Error "Python could not be started. Repair Python or add a working Python 3.11+ installation to PATH, then reopen PowerShell."
    exit 1
}

$pythonMajor = [int]$Matches[1]
$pythonMinor = [int]$Matches[2]
if ($pythonMajor -lt 3 -or ($pythonMajor -eq 3 -and $pythonMinor -lt 11)) {
    Write-Error "Python $pythonVersion is incompatible. Upgrade to Python 3.11 or newer, then reopen PowerShell."
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
if ($NonInteractive) {
    $pythonArgs += "--non-interactive"
}

& python @pythonArgs
exit $LASTEXITCODE
