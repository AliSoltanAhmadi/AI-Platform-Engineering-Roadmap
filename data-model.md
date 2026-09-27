# Data Model — Phase 1

Feature: Interactive CLI AI Platform Engineering Learning Tool (`specs/001-cli-learning-tool`).
Entities derived from spec user stories and `research.md` decisions. Storage under `.local/state/`.

## Entities

### Knowledge Base (read-only reference)

- Source: generated from `RoadMap/ai_platform_roadmap.md`.
- Fields per topic entry: `topic_id`, `title`, `phase`, `level_tags`, `explanation`, `next_step_action`, `related_topics[]`.
- Phase metadata: `phase_prerequisites` maps every phase name to the prerequisites shown before its next-step action.
- Relationship: referenced by roadmap-explainer flow (read-only lookup; not persisted per session).

### Progress Record (persisted)

- Path: `.local/state/progress.json` — schema-version field for future migrations.
- Fields: `level` (enum: beginner|intermediate|experienced), `completed_lessons[]`, `quiz_results[]` (lesson quiz and `assessment:pre|post:*` results with per-question id, score, attempts, timestamp), global `attempts`, `current_lesson`, `path_switches[]`, `revealed_lessons[]`, and `timestamps` (`created_at`, `updated_at`, `last_session_at`).
- Lifecycle: created on first session and accumulated across launches; reset replaces it with a canonical empty record only after the learner types the exact `RESET` confirmation.
- Validation: `level` restricted to the three enum values; arrays tolerate empty on fresh install.
- Migration: legacy aliases (`completed`, `revealed`, `last_session`) are converted to the canonical fields on load. Same-version partial records are repaired; unsupported future versions are never downgraded or overwritten.

### Model Registry (read-only reference)

- Fields per backend: `backend` (Ollama|vLLM|Deterministic Knowledge Base), `capability_level`, `default_model`.
- Ollama availability and installed model names are discovered at runtime from the loopback-only `/api/tags` endpoint with a bounded timeout.
- Roadmap generation may call `/api/generate` only with the matched local Knowledge Base topic as context; invalid, unavailable, or timed-out local responses fall back without blocking learning.
- Selection priority is installed Ollama → local vLLM OpenAI-compatible server → deterministic Knowledge Base responder; every HTTP endpoint is restricted to loopback.

### Learning Assessment (read-only definition)

- Source: `content/assessments.json`; exactly ten unique question ids and ten unique roadmap topic ids.
- The identical two-option probe set is loaded as `pre` and `post`; the pre-test is a non-blocking baseline and the post-test requires at least 80%.
- Path completion requires completed lessons, all path quiz questions correct, a recorded pre-test, and a passing post-test.

### Local Event Log (append-only measurement)

- Path: `.local/state/progress.events.jsonl` beside the progress record.
- Each line contains an ISO-8601 `timestamp`, `event_type`, and event-specific fields. Events include `session_started`, `onboarding_started`, `level_selected`, `assessment_started`, `assessment_completed`, `onboarding_completed`, and `path_completed`.
- `assessment_completed` includes score, pass state, and monotonic duration. The timestamps make onboarding and total path-completion duration derivable without remote telemetry.
- Reset removes the prior log and begins a new local history with `progress_reset`.

## Relationships & State Transitions

- Progress Record accumulates across sessions; challenge attempts update one idempotent `quiz_results` entry, and successful completion advances the learner's path position.
- Level selection influences which content (and first interactive task) is presented; changing level via overview preserves prior progress (path_switch recorded).
- A path cannot enter the complete state merely by displaying content; it requires persisted pre-test, lesson, quiz, and passing post-test evidence.
