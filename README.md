# CLI Learning Tool — AI Platform Engineering (US1 MVP)

Entry: `learn` | Tasks: T001, T013, T014, T015

## Quick start

Prerequisites: Windows PowerShell 5.1+ and Python 3.11+.

From a fresh PowerShell opened in the project directory:

```powershell
.\install.ps1
learn --help
learn --version
learn start
```

The installer is user-scoped, needs no Administrator access, and safely avoids duplicate PATH entries when rerun. The command is available immediately in the current PowerShell; reopen any older terminal windows to refresh their PATH.

If PowerShell blocks the installer, allow it only for the current process and retry:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

If Python is missing or older than 3.11, install a supported version and reopen PowerShell:

```powershell
winget install -e --id Python.Python.3.12
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

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
# From the parent directory:
python -m pytest -q .\AI_Platform_Engineering\tests
```
## Versions
Python 3.12, PowerShell 7 / 5.1 supported.
