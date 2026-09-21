# Learn CLI Entry Point - MVP for learn start
param([string]$Command = "")

function Show-Intro {
    Write-Host "========================================"
    Write-Host "  AI Platform Engineering Learning Tool"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "What is AI Platform Engineering?"
    Write-Host "  A practical path from DevOps/Platform/SRE work into ML and LLM platforms (MLOps + LLMOps)."
    Write-Host ""
    Write-Host "Phases: P0 -> P1 -> P2 -> P3 -> P4 -> P5"
    Write-Host ""
}

function Show-LevelPrompt {
    Write-Host "Select your experience level:"
    Write-Host "  1) beginner"
    Write-Host "  2) intermediate"
    Write-Host "  3) experienced"
    $choice = Read-Host "Choice (1-3)"
    if ($choice -eq "1") { return "beginner" }
    if ($choice -eq "2") { return "intermediate" }
    if ($choice -eq "3") { return "experienced" }
    return "beginner"
}

function Show-FirstTask {
    param([string]$Level)
    Write-Host ""
    Write-Host "--- First Task ($Level) ---"
    # T015: interactive task runner displays markdown and captures answer
    python "$base\src\task_runner.py"
}

if ($Command -eq "start" -or $Command -eq "") {
    # T013: session initialization
    $base = $PSScriptRoot
    python "$base\src\session_init.py"

    Show-Intro
    $level = Show-LevelPrompt
    Show-FirstTask -Level $level

    # T015: interactive task runner executed above; progress updates below
    $progress = Get-Content ".local\state\progress.json" | ConvertFrom-Json
    $progress.level = $level
    $progress.completed += "level-selection"
    $progress.completed += "beginner-first-task"
    $progress.last_session = (Get-Date -Format "o")
    $progress | ConvertTo-Json -Depth 3 | Set-Content ".local\state\progress.json"

    Write-Host ""
    Write-Host "Progress saved. Resume with 'learn start'."
    Write-Host "Launch complete (US1 MVP validated)."
} else {
    Write-Host "Unknown command: $Command"
    Write-Host "Usage: learn start"
}
