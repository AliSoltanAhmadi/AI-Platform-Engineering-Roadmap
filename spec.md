# Feature Specification: Interactive CLI AI Platform Engineering Learning Tool

**Feature Branch**: branch-001-cli-learning-tool

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: cli interactive ai platform engineering learning that starts with learn start

## User Scenarios & Testing (mandatory)

<!-- IMPORTANT: Prioritize user journeys by importance; each must be independently testable so a single one still yields a viable MVP. Assign priorities P1, P2, P3 -->

### User Story 1 - Onboard and begin a learning session (Priority: P1)

A learner opens a terminal and types learn start. The tool presents a warm welcome that explains what AI Platform Engineering is, then immediately routes them into an interactive guided journey based on their current experience level.

Why priority: This is the single entry point for every learner; without it there is no way to reach any other content. It delivers immediate value by turning an empty terminal into a guided tutor within seconds.

Independent Test: A fresh install with zero prior configuration can be launched solely via learn start, and the learner completes onboarding plus their first interactive step in one continuous session, proving end-to-end usability without any database, network access, or external accounts.

**Acceptance Scenarios:**:

1. Given an empty environment with no saved preferences, When a user types learn start and presses Enter, Then they are greeted with a brief intro to AI Platform Engineering followed by a level-selection prompt (beginner/intermediate/experienced).
2. Given the learner selects their experience level, When they confirm, Then the tool presents a first interactive task relevant to that level and waits for their response before advancing.

---

### User Story 2 - Explore the roadmap interactively (Priority: P2)

A learner can browse the AI Platform Engineering roadmap as an interactive, ask-and-answer conversation rather than scrolling through static prose. They query topics in natural language and receive a focused, stepwise explanation tied to the overall path.

Why priority: The repo core asset is RoadMap/ai_platform_roadmap.md. Turning it into an interactive explainer preserves that content while making it usable in terminal, a strong, independently shippable slice of value.

Independent Test: Starting only from the roadmap document, the tool answers topic queries drawn from the existing roadmap using the documented phases, without needing any external knowledge base or live endpoint.

**Acceptance Scenarios:**:

1. Given a loaded roadmap, When a user asks about a known topic from the roadmap, Then they receive an explanation that maps to the correct phase and next-step action.
2. Given an unknown or malformed query, When a user asks something not in scope, Then the tool politely explains it is outside this learning path and offers to return to the menu.
3. Given a learner has completed some lessons across sessions, When they restart the tool, Then their previous selections and completions are still available in an overview.
4. Given the user wants to switch tracks, When they choose a different topic from progress, Then the tool jumps to that section while preserving earlier progress.

---

### Edge Cases

- What happens when a learner types learn start but no terminal or CLI environment is available? — The tool treats it as an invalid command and returns to the menu rather than erroring out.
- How does the tool behave if its local content files are missing or empty (first run or partial install)? — It degrades gracefully to friendly onboarding that still lets the learner pick a level and attempt the first available challenge, with no crash.
- How should it handle an extremely long natural-language question, including very long multi-line input? — The tool accepts a single-line command (`learn start`) exactly as specified; for free-response topic queries, it bounds multi-line/very-long input to a fixed character limit and strips leading/trailing whitespace before routing the query to the Knowledge Base so the session degrades gracefully (polite answer or return-to-menu) instead of failing.
- What occurs when a learners chosen level has no associated practice lessons yet defined in the shipped content? — The tool still presents the first interactive task for that level; if no challenge exists, it offers the roadmap overview and returns to the menu rather than blocking progression.
- How does the tool respond if storage is read-only and progress cannot be saved? — It informs the learner that progress could not be saved, continues the session without failing, and persists any state only when storage becomes writable again.
---

### User Story 3 - Practice with interactive lessons and quizzes (Priority: P3)

A learner can move through hands-on, terminal-based practice items for each roadmap area, ending in a short quiz that checks understanding. Passing a lesson unlocks the next one along their chosen path.

Why priority: Practice cements learning better than reading and gives learners concrete proof of progress; it is the primary engagement loop of an interactive learning tool. It can be built as a self-contained module.

Independent Test: A learner completes one practice lesson followed by its associated quiz purely from locally stored content, receiving immediate feedback and either advancing or being prompted to retry, no network required.

**Acceptance Scenarios:**:

1. Given the learner is at an unlocked lesson, When they answer correctly, Then they advance to the next step in their path; And when they answer incorrectly, Then they are shown a hint and may retry without penalty beyond repetition.
2. Given a quiz is incomplete, When a learner attempts to move forward, Then they are stopped until each question has been answered at least once.

---

### User Story 4 - Track progress and return anywhere (Priority: P4)

A learners journey is remembered across sessions so they can resume where they left off, switch topics mid-path, and see a summary of what they have completed. Progress updates locally as they advance through lessons and quizzes.

Why priority: Persistence turns a one-off script into a reusable learning companion; it supports all other stories by letting learners pick up mid-journey. It can be delivered alongside any earlier story via local state.

Independent Test: A learner completes part of a path in one launch, exits, launches again, and sees their prior progress restored with the option to continue, using only local storage, no external services.

### Key Entities (include if feature involves data)

- Knowledge Base: The curated, local content derived from RoadMap/ai_platform_roadmap.md, organized by topic tag and roadmap phase so the on-device LLM can answer learner questions offline.
- Local Model Registry: The list of supported on-device inference backends (Ollama, vLLM) with their capability level; used to pick a model when none is preconfigured.
## Clarifications

### Session 2026-09-21

- Q: When a learner answers quiz/command-entry challenges, should their responses be recorded in any structured way that leaves the machine or project maintainers able to read them back? → A: Yes — store progress as plain local JSON (no encryption, no authN/Z).

## Requirements (mandatory)

<!-- ACTION REQUIRED: Fill out with concrete functional requirements. -->

### Functional Requirements

- FR-001: The tool MUST start an interactive session when the learner enters learn start (or its documented alias), accepting the command on a single line and confirming visually before proceeding.
- FR-002: The tool MUST guide the learner through an experience-level selection (at minimum beginner, intermediate, experienced) that influences which content is presented first.
- FR-003: The tool MUST run locally with an on-device LLM (e.g., Ollama or vLLM), using no cloud dependency, and answer roadmap topic queries by mapping each natural-language question to a phase and next-step action from the local Knowledge Base.
- FR-004: The tool MUST present free-response command-entry challenges for representative topics, capturing the learner's typed answer before scoring it against expected commands or patterns.
- FR-005: The tool MUST auto-score each challenge attempt, giving immediate feedback that either confirms completion on a correct entry or offers a hint and retry on an incorrect one.
- FR-006: The tool MUST persist learner progress (selected level, completed lessons, quiz results) locally so sessions can resume across separate launches. Progress is stored as plain local JSON under a local data directory with no encryption and no authentication gate; answers are human-readable for maintainers.
- FR-007: The tool MUST allow the learner to return to any section of their path at any time from a central menu or overview screen.
- FR-008: When asked about content outside this learning path, the tool MUST respond politely and offer to return to the main menu instead of erroring out.
- FR-009: Every interactive entry screen MUST state one clear next action; every recoverable error MUST explain what happened, why it happened, and what the learner should do next.
- FR-010: English MUST remain the default interface language, while `--lang fa` provides Persian navigation and beginner content. Both languages MUST preserve Unicode text in supported Windows PowerShell and terminal launches.
- FR-011: CI MUST reject invalid content schemas, failing tests, CLI smoke failures, scoring coverage below 90%, persistence coverage below 85%, and failures on either Windows PowerShell 5.1 or PowerShell 7. Release artifacts MUST depend on all quality and end-to-end gates succeeding.

## Assumptions

<!-- ACTION REQUIRED: Record reasonable defaults chosen where the description was silent. -->

- The tool is a command-line application run from a standard terminal and requires no graphical interface or web browser.
- Content is delivered from local files shipped with the tool; an internet connection and external AI service are not required for core learning flows (a live endpoint may be used as an optional enhancement in later versions).
- Progress is stored locally on the learners machine only, so no accounts or external databases are needed.
- Natural-language topic queries map to topics explicitly defined in RoadMap/ai_platform_roadmap.md; out-of-scope requests do not require any external knowledge source.
- Beginner content emphasizes DevOps/platform fundamentals (Linux, Docker/Kubernetes, CI/CD); experienced content emphasizes MLOps and LLMOps specifics such as GPU scheduling and RAG gateways.

## Success Criteria (mandatory)

<!-- ACTION RESOLVED: SC-002 topic-probe set + answer key defined; SC-003 given an instrumented, measurable pass threshold. All four criteria are technology-agnostic and testable without implementation details. -->

### Measurable Outcomes

- SC-001: A new learner can complete onboarding and their first interactive step within three minutes of starting the tool for the very first time, with no configuration.
- SC-002: Learners correctly identify at least 80% of roadmap topics they query after completing a basic path, versus below 50% before using the tool (measured on a short pre/post check).

**SC-002 measurement instrument (pre/post probe set).** Validation uses one fixed set of ten two-option questions. Every question has a unique topic id, one correct answer, and one plausible distractor. The same set is used before and after a path so the scores are directly comparable:

1. Pulling a public container image without starting it (`docker pull`).
2. Giving a set of Kubernetes Pods a stable network endpoint (Service).
3. Loading tabular CSV data for inspection (`pandas.read_csv`).
4. Versioning datasets alongside code for reproducible ML work (DVC).
5. Recording experiment parameters, metrics, and artifacts (MLflow).
6. Keeping training and serving features consistent (feature store).
7. Representing multi-step training as Kubernetes workflows (Argo Workflows).
8. Serving LLM inference with continuous batching (vLLM).
9. Retrieving relevant documents before answer generation (RAG).
10. Demonstrating end-to-end ability with a documented working mini-platform.

**Pass thresholds:** The pre-path score is recorded as a non-blocking baseline; the SC-002 validation cohort target remains below 50%. A learner completes the path only after scoring at least 80% (eight or more of ten) on the post-test.

### SC-002 Note
The pre/post check is a short, repeatable quiz over the probe set above — not a production workload. It validates learner comprehension of roadmap topics rather than system performance.

- SC-003: Learners complete their first practice lesson and its full quiz within five minutes during a single continuous session without reinstalling or seeking external help; at least 90% of learners meet this outcome on the happy path (no network, no external accounts).
- SC-004: Learners can resume an interrupted path successfully within two minutes of returning, with no loss of prior progress.

### Local Inference (mandatory)

The feature uses on-device LLM inference only — no cloud dependency or network call is required for any learning flow. The model selection follows this priority order:

1. Use a preconfigured local model if one is already available in the learner environment (e.g., via Ollama).
2. Otherwise, fall back to a bundled lightweight model so inference still works out of the box.
3. Clearly tell the learner which model is active and that no external service is contacted during learning.

### Local Model Registry

The set of supported on-device inference backends (Ollama, vLLM) with their capability level; used to pick a model when none is preconfigured.

