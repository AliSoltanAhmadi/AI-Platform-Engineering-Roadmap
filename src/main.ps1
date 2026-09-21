# Main CLI dispatcher / menu loop — MVP skeleton per spec
param([string]$Action = "start")

$root = $PSScriptRoot | Resolve-Path | Select-Object -ExpandProperty Path
# Future: load content/tasks, route to session_init, task_runner, persist
Write-Host "[main] Dispatcher: $Action from $root"
