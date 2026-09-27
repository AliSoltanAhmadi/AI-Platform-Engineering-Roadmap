# Quality Gates

The authoritative CI workflow is `.github/workflows/quality.yml`. Pull requests, pushes, manual runs, and tag pushes execute these gates:

1. Validate every JSON file under `content/` and `contracts/`, then validate cross-file references between levels, lessons, quizzes, challenges, roadmap topics, assessments, runtime progress fields, and command contracts.
2. Run the complete pytest suite.
3. Require at least 90% statement coverage for `src/scoring` and 85% for `src/persist`.
4. Run a real `learn.ps1` CLI smoke test.
5. Run English and Persian smoke tests under both Windows PowerShell 5.1 (`Desktop`) and PowerShell 7 (`Core`).
6. Run the required end-to-end test group explicitly.

Tag-triggered release packages declare `needs: [quality, windows-shells, end-to-end]`. Therefore no release artifact is built when any test, schema check, coverage threshold, shell compatibility check, smoke test, or required end-to-end test is red or missing.

## Local command

From Windows PowerShell:

```powershell
.\scripts\quality_gate.ps1
```

The local gate runs schema validation, the full suite, both coverage thresholds, and a real CLI smoke test. PowerShell 7 compatibility remains enforced by the CI matrix when `pwsh` is unavailable on the developer machine.
