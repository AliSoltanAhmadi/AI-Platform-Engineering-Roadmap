# CLI Learning Tool — AI Platform Engineering (US1 MVP)

Entry: `learn.ps1` | Tasks: T013, T014, T015

## Quick start
```powershell
function learn { param([string]$c); .\learn.ps1 $c }
learn start
```

## Project structure
```
cli-learning-tool/
├── learn.ps1                      # entry point
├── README.md                       # this file
├── src/
│   ├── session_init.py             # T013
│   ├── task_runner.py              # T015
│   ├── main.ps1                    # dispatcher
│   ├── persist/progress_store.py
│   ├── llm/ollama_client.py
│   ├── llm/bundled_model.py
│   └── scoring/challenge_scorer.py
├── content/tasks/beginner_first_task.md  # T014
├── contracts/
├── tests/
└── .local/state/progress.json      # runtime
```

## Completed
- T013 session initialization, T014 beginner content, T015 interactive runner
- Non-interactive production path validated for wrong answer, correct answer, persistence, and idempotent resume

## Not completed yet
- The full Quickstart Scenario 1 roadmap-explainer conversation is not yet implemented or validated.
- Interactive multi-lesson navigation remains planned work.

## Test / CI
Requires Python >=3.11, PowerShell 5.1+.
```powershell
pip install -r requirements-dev.txt
python -m pytest -q
# From the parent directory:
python -m pytest -q .\AI_Platform_Engineering\tests
```
## Versions
Python 3.12, PowerShell 7 / 5.1 supported.
