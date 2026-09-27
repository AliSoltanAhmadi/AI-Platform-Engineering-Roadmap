[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "AIPlatformLearning\bin"),
    [ValidateSet("User", "Process")]
    [string]$PathScope = "User",
    [string]$StatePath = ".local/state/progress.json",
    [switch]$RemoveState
)

$ErrorActionPreference = "Stop"
$resolvedInstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$shimPath = Join-Path $resolvedInstallDir "learn.cmd"

if (Test-Path -LiteralPath $shimPath -PathType Leaf) {
    Remove-Item -LiteralPath $shimPath -Force
    Write-Host "Removed learn command: $shimPath"
} else {
    Write-Host "The learn command was not installed at: $shimPath"
}

if ($PathScope -eq "User") {
    $savedPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $remaining = @($savedPath -split ";" | Where-Object {
        $_ -and $_.TrimEnd("\") -ine $resolvedInstallDir.TrimEnd("\")
    })
    [Environment]::SetEnvironmentVariable("Path", ($remaining -join ";"), "User")
}

$processRemaining = @($env:Path -split ";" | Where-Object {
    $_ -and $_.TrimEnd("\") -ine $resolvedInstallDir.TrimEnd("\")
})
$env:Path = $processRemaining -join ";"

if ((Test-Path -LiteralPath $resolvedInstallDir -PathType Container) -and
    -not (Get-ChildItem -LiteralPath $resolvedInstallDir -Force | Select-Object -First 1)) {
    Remove-Item -LiteralPath $resolvedInstallDir -Force
}

$resolvedStatePath = [System.IO.Path]::GetFullPath($StatePath)
$eventPath = [System.IO.Path]::ChangeExtension($resolvedStatePath, ".events.jsonl")
if ($RemoveState) {
    foreach ($path in @($resolvedStatePath, $eventPath)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Remove-Item -LiteralPath $path -Force
            Write-Host "Removed local state file: $path"
        }
    }
} else {
    Write-Host "Progress was preserved at: $resolvedStatePath"
    Write-Host "To remove it too, rerun with -RemoveState and the same -StatePath."
}

Write-Host "Uninstall complete. Reopen other terminals to refresh their PATH."
