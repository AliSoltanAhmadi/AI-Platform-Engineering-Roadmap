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
- T013 session init, T014 beginner content, T015 interactive runner
- Validated via quickstart.md Scenario 1 (onboarding + first task + persistence)
