# Thin PowerShell launcher for the Python session orchestrator.
param(
    [string]$Command = "start",
    [string]$Level,
    [string]$Answer,
    [string]$StatePath,
    [switch]$NonInteractive
)

if ($Command -ne "start") {
    Write-Error "Unknown command: $Command"
    Write-Host "Usage: learn start [-Level 1] [-Answer 'docker pull nginx'] [-NonInteractive]"
    exit 64
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
