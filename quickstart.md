# Quickstart Validation Guide — Phase 1

Feature: Interactive CLI AI AI Platform Engineering Learning Tool (`specs/001-cli-learning-tool`).
Runnable end-to-end validation scenarios proving the feature works. References `data-model.md` and `/contracts/*.json`; does not include full implementation code.

## Prerequisites

- A standard terminal / shell; no graphical interface or web browser required.
- Fresh install with zero prior configuration (simulates a first-run learner).
- Optional: Ollama installed locally (`ollama list`) to exercise the preconfigured-model path. The bundled-fallback path must work even without it.

## Scenario 1 — End-to-end happy path

Proves User Story 1 + User Story 3, and satisfies SC-001/SC-004 (first run in ≤3 min; resume across launches).

1. Launch the tool with `learn start`.
2. Expect a brief AI Platform Engineering intro, then a level-selection prompt (`beginner` / `intermediate` / `experienced`).
3. Select `beginner` and confirm.
4. Expect a first interactive task relevant to that level; answer it free-response.
5. For the roadmap-explainer flow: ask a known topic in natural language (e.g., "how do I pull an image?") and expect an explanation mapped to a phase + next-step action from the local Knowledge Base (`contracts/knowledge-base.json`).
6. Encounter a command-entry challenge; answer with `docker pull nginx` — accept both `docker pull` and `podman pull` per `contracts/challenge-definition.json`. Expect immediate confirm/hint feedback.
7. Exit, relaunch, type `learn start`, expect prior progress restored from `.local/state/progress.json` (schema_version 1.0.0) with a continue option.

## Interface language and terminal encoding

- English is the default product language: `learn start -Lang en` in PowerShell or `python src/session.py start --lang en`.
- Persian navigation and the localized beginner first task are available with `learn start -Lang fa` or `--lang fa`.
- `learn.ps1` enables UTF-8 Python output and UTF-8 console encoding so Persian text and symbols such as `✓` render consistently in Windows PowerShell and modern terminals.
- Recoverable failures always state what happened, why it happened, and the next action.

## Scenario 2 — Out-of-scope & error handling

Proves User Story 2 acceptance scenarios and Edge Cases in spec.

- Ask about content outside the learning path → expect polite response offering to return to the main menu (no error).
- Answer a challenge incorrectly → expect hint + retry without penalty beyond repetition.
- Empty/missing local content files on first run → tool degrades gracefully instead of crashing.

## Scenario 3 — Local inference & persistence

Proves User Story 4 and Local Inference contract.

- With Ollama present: confirm the active model is reported as preconfigured; no network call made.
- Without Ollama/network: confirm bundled lightweight fallback activates and progress still persists locally (no accounts, no external services).
