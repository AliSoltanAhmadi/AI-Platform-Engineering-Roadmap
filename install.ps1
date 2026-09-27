[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "AIPlatformLearning\bin"),
    [ValidateSet("User", "Process")]
    [string]$PathScope = "User"
)

$ErrorActionPreference = "Stop"

$launcher = Join-Path $PSScriptRoot "learn.ps1"
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "Launcher not found: $launcher"
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Python was not found. Install Python 3.11 or newer (for example: winget install -e --id Python.Python.3.12), then reopen PowerShell."
}

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^(\d+)\.(\d+)$') {
    throw "Python could not be started. Repair Python or add a working Python 3.11+ installation to PATH."
}

$pythonMajor = [int]$Matches[1]
$pythonMinor = [int]$Matches[2]
if ($pythonMajor -lt 3 -or ($pythonMajor -eq 3 -and $pythonMinor -lt 11)) {
    throw "Python $pythonVersion is incompatible. Upgrade to Python 3.11 or newer."
}

$resolvedInstallDir = [System.IO.Path]::GetFullPath($InstallDir)
New-Item -ItemType Directory -Path $resolvedInstallDir -Force | Out-Null

$shimPath = Join-Path $resolvedInstallDir "learn.cmd"
$shim = @"
@echo off
if /I "%~1"=="--help" goto help
if /I "%~1"=="-h" goto help
if /I "%~1"=="--version" goto version
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$launcher" %*
exit /b %errorlevel%

:help
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$launcher" -Command "--help"
exit /b %errorlevel%

:version
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$launcher" -Command "--version"
exit /b %errorlevel%
"@
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($shimPath, $shim, $utf8WithoutBom)

if ($PathScope -eq "User") {
    $savedPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $savedEntries = @($savedPath -split ";" | Where-Object { $_ })
    $alreadySaved = $savedEntries | Where-Object {
        $_.TrimEnd("\") -ieq $resolvedInstallDir.TrimEnd("\")
    }
    if (-not $alreadySaved) {
        $newPath = (@($savedEntries) + $resolvedInstallDir) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    }
}

$processEntries = @($env:Path -split ";" | Where-Object { $_ })
$alreadyActive = $processEntries | Where-Object {
    $_.TrimEnd("\") -ieq $resolvedInstallDir.TrimEnd("\")
}
if (-not $alreadyActive) {
    $env:Path = "$resolvedInstallDir;$env:Path"
}

Write-Host "Installed learn command: $shimPath"
if ($PathScope -eq "User") {
    Write-Host "User PATH updated. The command is ready now; reopen other terminals to refresh their PATH."
}
Write-Host "Try: learn --help"
