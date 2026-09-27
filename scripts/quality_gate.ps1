param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$statePath = $null
Push-Location $projectRoot
try {
    & python scripts/validate_schemas.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & python -m pytest -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & python -m pytest tests/unit/test_challenge_scorer.py tests/unit/test_t004_scoring.py tests/unit/test_t005_learning_loop.py -q --cov=src/scoring --cov-report=term-missing --cov-fail-under=90
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & python -m pytest tests/unit/test_persist.py tests/unit/test_t006_progress_model.py -q --cov=src/persist --cov-report=term-missing --cov-fail-under=85
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $statePath = Join-Path ([System.IO.Path]::GetTempPath()) ("learn-quality-" + [guid]::NewGuid() + ".json")
    & .\learn.ps1 start -Level 1 -Answer "docker pull nginx" -StatePath $statePath -NonInteractive
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Quality gate passed: schemas, tests, coverage, and CLI smoke are green."
}
finally {
    if ($statePath -and (Test-Path -LiteralPath $statePath)) {
        Remove-Item -LiteralPath $statePath -Force
    }
    Pop-Location
}
