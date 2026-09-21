# Research Findings — Phase 0

Feature: Interactive CLI AI Platform Engineering Learning Tool (`specs/001-cli-learning-tool`).
Fully local, single-user; content derived from `RoadMap/ai_platform_roadmap.md`.

## Technical Context Resolutions (NEEDS CLARIFICATION resolved)

### Research 1 — Local LLM orchestration in PowerShell+Python hybrid

- Decision: Wrap Ollama REST API via a Python helper invoked through `[Net.HttpClient]` from PowerShell. Keep model discovery, prompt assembly, and response parsing inside the Python module so it can stream token-by-token to the terminal.
- Rationale: PowerShell lacks a native LLM client; calling the standard Ollama `/api/generate` JSON endpoint avoids extra dependencies while fitting the existing tool layer (which is hostile to shell-special characters).
- Alternatives considered: Direct cURL from PowerShell (fragile with character stripping); full Python app (breaks single-command `learn start` UX and library-first principle); native C# bindings (heavier than a thin HTTP wrapper).

### Research 2 — Free-response command scoring strategy

- Decision: Multi-answer pattern matching per challenge. Acceptance set = canonical form + common variants (e.g., `podman pull nginx`, `docker pull nginx`), normalized by stripping arguments and case-folding the first token. Provide hint on mismatch, retry with no penalty beyond repetition.
- Rationale: Learners will vary syntax; a strict exact-match fails benign equivalent entries. Normalizing to the primary verb + repository gives deterministic scoring while tolerating tool naming (podman vs docker).
- Alternatives considered: LLM-judged correctness (unreliable, network-dependent, contradicts local-only constraint); regex-per-command (brittle for argument ordering); single-canonical-answer (rejects legitimate variants).

### Research 3 — Local persistence format & versioning

- Decision: JSON documents under `specs/001-cli-learning-tool/.local/state/` with a schema-version field. Progress record = level, completed lessons, quiz results, timestamps; knowledge base and model registry are read-only reference files (not persisted per-session).
- Rationale: Plain JSON satisfies the Q&A decision (no encryption/auth) and keeps state human-readable for maintainers. A version header lets future migrations fail safe on incompatible records.
- Alternatives considered: SQLite/PSData-style store (overkill, adds a dependency); binary formats (breaks the "human-readable" requirement).

## Best Practices

### Local inference best practices
- Detect Ollama via `ollama list` / API health probe before each session; if absent or no models, fall back to a bundled lightweight model shipped in the repo. Always tell the learner which model is active and that no external service is contacted.
- No network call required for any learning flow — degrade gracefully from preconfigured → bundled fallback → inform-and-proceed.

### Free-response scoring best practices
- Score deterministically (no LLM needed); keep acceptance sets small and documented in each challenge definition so maintainers can audit fairness. Show feedback immediately, allow unlimited retries without penalty beyond repetition.

### Roadmap Phase P2–P5 knowledge content (from ai_platform_roadmap.md)
- **P2 Core MLOps**: anchor challenges on KodeKloud 100 Days of MLOps task vocabulary (DVC, MLflow, Feast, FastAPI/BentoML). Exit criteria: 100 Days badge + public notes repo.
- **P3 K8s-as-ML-platform**: practice KServe/InferenceService manifests, Argo Workflows for training Jobs, GitOps deploy. Exit: GitOps-managed model endpoint (Helm/Kustomize + Argo CD) with health checks and rollback runbook.
- **P4 LLMOps/GPU scheduling**: vLLM model servers, RAG infra, LLM gateways (auth/rate-limit/fallback/token cost), `nvidia.com/gpu` device-plugin scheduling, DCGM metrics → Prometheus/Grafana. Exit: design doc "How I schedule vLLM on K8s" + a local Ollama CPU/RAG demo.
- **P5 Portfolio**: three public projects (MLOps mini-platform; K8s model serve; LLM platform slice) mapped to DevOps→AI Platform career packaging.

<!-- Phase 0 Bridge P0–P1 prerequisites: Docker Compose FastAPI hello app, Pod/Deployment/Service mental model, ML vocabulary for platform people. -->

## Next Steps

1. Phase 1: generate `data-model.md` entities from the above decisions.
2. Generate `/contracts/`: command schema, knowledge-base JSON schema, progress-record JSON schema, challenge-definition schema.
3. Create `quickstart.md` runnable validation scenarios (fresh install → complete lesson + quiz → resume).
