# Data Model — Phase 1

Feature: Interactive CLI AI Platform Engineering Learning Tool (`specs/001-cli-learning-tool`).
Entities derived from spec user stories and `research.md` decisions. Storage under `.local/state/`.

## Entities

### Knowledge Base (read-only reference)

- Source: generated from `RoadMap/ai_platform_roadmap.md`.
- Fields per topic entry: `topic_id`, `title`, `phase`, `level_tags`, `explanation`, `next_step_action`, `related_topics[]`.
- Relationship: referenced by roadmap-explainer flow (read-only lookup; not persisted per session).

### Progress Record (persisted)

- Path: `.local/state/progress.json` — schema-version field for future migrations.
- Fields: `level` (enum: beginner|intermediate|experienced), `completed_lessons[]`, `quiz_results[]` (per-question id, score, attempts, timestamp), global `attempts`, `current_lesson`, `path_switches[]`, `revealed_lessons[]`, and `timestamps` (`created_at`, `updated_at`, `last_session_at`).
- Lifecycle: created on first session, appended across launches; never deleted without explicit learner action.
- Validation: `level` restricted to the three enum values; arrays tolerate empty on fresh install.
- Migration: legacy aliases (`completed`, `revealed`, `last_session`) are converted to the canonical fields on load. Same-version partial records are repaired; unsupported future versions are never downgraded or overwritten.

### Model Registry (read-only reference)

- Fields per backend: `backend` (Ollama|vLLM), `capability_level`, `default_model`.
- Used only when no preconfigured model is available in the learner environment.

## Relationships & State Transitions

- Progress Record accumulates across sessions; challenge attempts update one idempotent `quiz_results` entry, and successful completion advances the learner's path position.
- Level selection influences which content (and first interactive task) is presented; changing level via overview preserves prior progress (path_switch recorded).
