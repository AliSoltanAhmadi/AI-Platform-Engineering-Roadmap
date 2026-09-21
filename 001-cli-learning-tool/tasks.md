# Tasks: 001 CLI Learning Tool

**Input**: Design documents from `/specs/001-cli-learning-tool/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create feature directory structure under `specs/001-cli-learning-tool/` with subdirectories for PowerShell scripts, Python modules, tests, and `.local/state/`
- [ ] T002 Initialize PowerShell module manifest (`001-cli-learning-tool.psm1`) and add stub functions for CLI entry points (learn start, learn overview)
- [ ] T003 Create initial `.gitignore` covering `__pycache__/`, `.local/`, Python egg-info, IDE artifacts, and OS temp files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

### TDD Order — Write tests first (ensure they fail), then implement

- [ ] T004 Create contract test for progress.json schema in `tests/contracts/test_progress_schema.json` validating fields: level, completed_lessons[], quiz_results[]
- [ ] T005 Create unit test for session persistence layer (`tests/unit/test_persist.py`) covering read/write of `.local/state/progress.json` with error handling

### Implementation

- [ ] T006 Implement progress persistence module in `src/persist.py` using plain JSON (no database, no auth) — write to `.local/state/progress.json` on disk
- [ ] T007 Implement knowledge base generator script in `src/generate_kb.py` that reads `RoadMap/ai_platform_roadmap.md` and produces `contracts/knowledge-base.json` with topic entries tagged by phase (bridge, ml-literacy, mlops, k8s-ml-platform, llmops-gpu, portfolio)
- [ ] T008 Implement local model registry in `src/model_registry.py` — detect preconfigured Ollama models; if none found, fall back to bundled lightweight model with capability level reporting

---

## Phase 3: User Story 1 - Onboard and begin a learning session (Priority: P1) 🎯 MVP

**Goal**: Learner launches `learn start`, receives intro + level selection prompt, then starts first interactive task relevant to their chosen level.

**Independent Test**: A fresh install with zero prior configuration can be launched via `learn start` and complete onboarding plus the first interactive step in one continuous session without any database, network access, or external accounts.

### Implementation for User Story 1

- [ ] T010 Create main CLI entry script at `src/main.ps1` implementing command router for `learn start`, `learn overview`, and error handling
- [ ] T011 Implement welcome function in `src/welcome.py` that displays AI Platform Engineering intro text (plain markdown or formatted output)
- [ ] T012 Create level selection prompt in `src/level_select.ps1` offering beginner/intermediate/experienced options with validation for exact-match user input
- [ ] T013 Implement session initialization logic in `src/session_init.py` that creates `.local/state/progress.json` on first launch with schema_version 1.0.0 and default level set by user choice
- [ ] T014 Create beginner-level first task content file at `content/tasks/beginner_first_task.md` (introduces AI Platform Engineering basics per roadmap P0 bridge phase)
- [ ] T015 Implement interactive task runner in `src/task_runner.py` that displays content from markdown files and captures user free-response answers

---

## Phase 4: User Story 2 - Explore the roadmap interactively (Priority: P2)

**Goal**: Learner queries topics in natural language and receives explanations mapped to phases + next-step actions from local knowledge base.

**Independent Test**: Starting only from RoadMap/ai_platform_roadmap.md, the tool answers topic queries drawn from existing roadmap using documented phases without needing external knowledge base or live endpoint.

### Tests for User Story 2 (optional — not requested but recommended)

- [ ] T016 Create contract test file at `tests/contracts/test_explainer_responses.json` with probe questions and expected phase mappings (topic_id → phase, explanation presence)
- [ ] T017 Create unit test in `tests/unit/test_explainer.py` covering: known topic query → correct phase mapping; unknown/malformed query → polite out-of-scope response + menu offer

### Implementation for User Story 2

- [ ] T018 Implement roadmap explainer module in `src/explainer.py` that loads `contracts/knowledge-base.json` and matches user queries to topic entries using pattern matching
- [ ] T019 Create interactive chat interface in `src/chat.ps1` that prompts for natural language input, displays explanation + phase mapping + next-step action from knowledge base
- [ ] T020 Implement graceful degradation handler in `src/fallback.py` that returns friendly response when no matching topic found (handles missing files, empty KB)

---

## Phase 5: User Story 3 - Free-response challenge engine with multi-answer scoring (Priority: P3)

**Goal**: Learner answers command-based challenges; tool accepts multiple valid answers and scores based on percentage correct over a fixed probe set.

**Independent Test**: Tool correctly accepts both `docker pull nginx` and `podman pull nginx` for the same challenge, reports 10/10 score when all ten probe questions answered correctly, and 0/10 when none correct.

### Implementation for User Story 3

- [ ] T021 Create challenge definitions in `content/challenges/command_probes.json` with ten probe questions, each containing one correct answer set and plausible distractors (per SC-002)
- [ ] T022 Implement scoring engine in `src/scoring.py` that computes percentage-correct score on the fixed probe set before and after a learning path
- [ ] T023 Create interactive challenge presenter in `src/challenge.ps1` that displays question, accepts free-response answer, validates against accepted answers (both docker pull and podman pull), and provides immediate feedback/hint
- [ ] T024 Implement threshold check function in `src/threshold.py` that evaluates pre-path baseline (<50% correct) vs post-path result (≥80% correct per SC-003)

---

## Phase 6: User Story 4 - Interactive menu / overview with resume capability (Priority: P4)

**Goal**: Learner sees progress summary from `.local/state/progress.json` and can switch tracks while preserving prior progress.

### Implementation for User Story 4

- [ ] T025 Implement overview function in `src/overview.ps1` that reads progress record and displays level, completed lessons list, quiz results summary
- [ ] T026 Create path switching logic in `src/path_switch.py` that updates current lesson pointer while recording `path_switches[]` entry with timestamp (preserves prior progress)
- [ ] T027 Implement resume flow in `src/resume.ps1` that detects prior session, offers continue option within 2 minutes of relaunch (SC-004 requirement), and restores saved state

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T030 Update documentation in `docs/` with usage examples for all commands (`learn start`, `learn overview`)
- [ ] T031 Run quickstart.md validation scenarios (Scenario 1: happy path, Scenario 2: out-of-scope/error handling, Scenario 3: local inference + persistence)
- [ ] T032 Code cleanup and formatting across all PowerShell/Python modules
- [ ] T033 Verify versioning follows MAJOR.MINOR.PATCH convention in `.local/state/progress.json` schema

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion; user stories can proceed in parallel or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models/persistence before services/modules
- Core modules before interactive UIs
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- T004, T005 unit/contract tests for persistence can be written in parallel (Phase 2)
- T016, T017 explainer tests can be written in parallel with UI implementation (Phase 4)
- Different user stories can be worked on in parallel by different team members once Foundational phase is done

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently per quickstart Scenario 1
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3, then 4 → Each story adds value without breaking previous stories
