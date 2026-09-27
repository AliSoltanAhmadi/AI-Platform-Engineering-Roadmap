# AI Platform Engineering Learning CLI

A local, beginner-oriented command-line learning tool for moving from DevOps, Platform Engineering, or SRE toward MLOps and LLMOps. It provides level-specific lessons, command exercises, quizzes, roadmap explanations, pre/post assessments, resumable progress, and English or Persian navigation.

Core learning works offline. No account, cloud model, browser, or external API is required.

## Requirements

- Windows PowerShell 5.1 or PowerShell 7
- Python 3.11 or newer available as `python`
- A persistent checkout of this repository; the installed `learn` shim points back to `learn.ps1` here
- Ollama or vLLM is optional

## Install

Open PowerShell in the repository directory:

```powershell
Set-ExecutionPolicy -Scope Process Bypass   # only if script execution is blocked
.\install.ps1
learn --help
learn --version
```

The installer:

- requires no Administrator access;
- creates `%LOCALAPPDATA%\AIPlatformLearning\bin\learn.cmd`;
- adds that directory to the user PATH without duplicating it;
- makes `learn` available immediately in the current PowerShell session.

Reopen older terminal windows so they receive the updated PATH. Do not move or delete the repository after installation unless you reinstall from its new location.

For a temporary process-only installation or a custom directory:

```powershell
.\install.ps1 -PathScope Process -InstallDir "$env:TEMP\ai-learning-bin"
```

## First run

```powershell
learn start
```

Then:

1. Choose **Continue**.
2. Select beginner, intermediate, or experienced.
3. Complete the ten-question pre-test; it records a baseline and does not block learning.
4. Enter the requested command in the first exercise. For the beginner path, `docker pull nginx` is accepted.
5. Continue through lessons and the quiz, then score at least 8/10 on the post-test to complete the path.

Progress is saved automatically. Running `learn start` again resumes the current stage.

Persian navigation and localized beginner content:

```powershell
learn start -Lang fa
```

Non-interactive smoke example:

```powershell
learn start -Level 1 -Answer "docker pull nginx" -NonInteractive
```

## Local inference

The startup message always reports the selected backend. Selection order is Ollama, then vLLM, then the deterministic local Knowledge Base responder. Ollama and vLLM endpoints are restricted to loopback addresses and have short timeouts.

### With Ollama

Ollama is optional. If it is already running on `http://localhost:11434` and `ollama list` reports at least one installed model, the tool uses the first reported model for Knowledge-Base-grounded roadmap answers.

```powershell
ollama list
learn start
```

Expected startup line:

```text
Active local model: ollama/<installed-model>
```

Stopping Ollama does not block onboarding, scoring, quizzes, assessments, or persistence.

### Without Ollama

No setup is necessary. The tool checks a loopback vLLM OpenAI-compatible server at `http://localhost:8000`. If neither local server is available, it uses the deterministic Knowledge Base responder:

```text
Active local model: deterministic/knowledge-base-v1
Inference scope: deterministic local Knowledge Base fallback; no network used.
```

This fallback still supports the complete learning flow. It is deterministic rather than a general-purpose language model.

## State, privacy, and reset

By default, state is relative to the directory where `learn start` is run:

```text
.local/state/progress.json
.local/state/progress.events.jsonl
```

- `progress.json` contains selected level, completed lessons, quiz/assessment scores, attempts, and timestamps.
- `progress.events.jsonl` is an append-only local measurement log for onboarding and completion events.
- Both files are plain text, local only, and contain no authentication or encryption.
- Use the menu's **Reset all progress** action and type the exact confirmation `RESET` for an in-product reset.

To keep state in a known location, launch directly with an explicit path:

```powershell
.\learn.ps1 start -StatePath "$env:LOCALAPPDATA\AIPlatformLearning\state\progress.json"
```

Use the same `-StatePath` on later runs.

## Uninstall

Remove the command and its PATH entry while preserving progress:

```powershell
.\uninstall.ps1
```

If a custom installation directory was used, supply the same values:

```powershell
.\uninstall.ps1 -InstallDir "$env:TEMP\ai-learning-bin" -PathScope Process
```

State is deliberately preserved by default. To remove the two known state files as well:

```powershell
.\uninstall.ps1 -RemoveState -StatePath ".local\state\progress.json"
```

The uninstaller does not recursively delete the repository or arbitrary directories.

## Troubleshooting

### Python is missing or too old

Check the interpreter:

```powershell
python --version
```

Install Python 3.11+ and reopen PowerShell:

```powershell
winget install -e --id Python.Python.3.12
```

If Python is installed but does not start, repair the installation or place its executable on PATH.

### `learn` is not recognized

Older terminals do not receive PATH changes made after they opened. Reopen PowerShell, or reinstall for the current process:

```powershell
.\install.ps1 -PathScope Process
Get-Command learn
```

Also confirm that the original repository and `learn.ps1` still exist at the location used during installation.

### Persian text or Unicode symbols look corrupted

Use Windows PowerShell 5.1 or PowerShell 7 and launch through `learn.ps1`/`learn`. The launcher enables UTF-8 Python and console output. If the host was previously reconfigured, start a new terminal and use a font with Persian glyph support.

```powershell
learn start -Lang fa
```

### Progress cannot be saved (read-only storage)

The state directory must be writable. Choose a writable explicit path and reuse it on every launch:

```powershell
.\learn.ps1 start -StatePath "$env:LOCALAPPDATA\AIPlatformLearning\state\progress.json"
```

Do not place state under a read-only checkout, protected system directory, or read-only volume. A save failure is reported with what happened, why, and the next action; the tool does not silently claim that progress was persisted.

### Content or JSON validation fails

Restore the shipped `content/` and `contracts/` files, then run:

```powershell
python scripts\validate_schemas.py
```

The validator checks JSON structure and cross-file references among levels, lessons, quizzes, challenges, roadmap topics, assessments, progress fields, and commands.

### Ollama or vLLM is unavailable

This is not fatal. Confirm the startup backend line. If deterministic fallback is active, all required learning features remain available. If a local model is expected, verify `ollama list` or the vLLM `/v1/models` endpoint on loopback and restart the session.

## Capability status

### Active

- User-scoped Windows installer and safe uninstaller
- Beginner, intermediate, and experienced paths
- Free-response command scoring, hints, retries, quizzes, and pre/post assessment
- Local progress/resume/reset and local timing events
- Roadmap exploration grounded in the shipped Knowledge Base
- Offline deterministic fallback and loopback-only Ollama/vLLM selection
- English navigation plus Persian navigation and localized first beginner task
- CI schema, test, coverage, PowerShell compatibility, CLI smoke, and release gates

### Experimental

- Natural-language generation through a user's local Ollama or vLLM server
- Persian localization beyond navigation and the first beginner task
- Scripted novice-persona usability evidence; this is not yet moderated human research

### Planned

- Moderated usability sessions with at least three first-time human learners
- Broader Persian translation of lessons, quizzes, and roadmap explanations
- Installers and compatibility testing for non-Windows operating systems

## Development and quality gates

```powershell
python -m pip install -r requirements-dev.txt
.\scripts\quality_gate.ps1
```

Current required minimum coverage is 90% for `src/scoring` and 85% for `src/persist`. See [docs/quality-gates.md](docs/quality-gates.md) for the CI and release gates.

## Project layout

```text
learn.ps1 / install.ps1 / uninstall.ps1   PowerShell entry points
src/session.py                             CLI orchestration
src/scoring/                               Challenge scoring
src/persist/                               Versioned progress storage
src/content/                               Lessons, quizzes, assessments, roadmap loading
src/llm/                                   Ollama, vLLM, and deterministic fallback
src/telemetry/                             Local JSONL event log
content/                                   Shipped learning material and Knowledge Base
contracts/                                 Runtime data/command contracts
scripts/                                   Schema and local quality gates
tests/                                     Unit, integration, smoke, and end-to-end tests
```
