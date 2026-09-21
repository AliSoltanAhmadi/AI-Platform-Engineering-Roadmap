# Implementation Plan: Interactive CLI AI Platform Engineering Learning Tool

- Feature directory: `specs/001-cli-learning-tool`
- Spec file: `spec.md`
- Branch: `001-cli-learning-tool`
- Created: 2026-09-21
- Design decisions recorded in Q&A session (see `checklists/requirements.md`).

## Technical Context

- **Stack**: PowerShell core + Python for on-device LLM orchestration. The tool layer is hostile to certain characters (`:`, trailing `)` / `}`), so structural edits use exact-match replacements and JSON uses `[char]34` for quotes in the fragile shell path.
- **Scope**: Fully local — no cloud dependency, no accounts, single-user. Content derived from `RoadMap/ai_platform_roadmap.md`, which spans 6 phases: P0 Bridge (Docker/K8s/Python glue), P1 ML literacy, P2 Core MLOps (KodeKloud 100 Days), P3 K8s-as-ML-platform (Helm/GitOps/KServe), P4 LLMOps/GPU scheduling/gateway/security (vLLM, `nvidia.com/gpu`, DCGM), P5 Portfolio & career packaging.
- **Inference**: on-device LLM only (Ollama/vLLM); model-selection priority preconfigured → bundled fallback → inform learner. See spec "Local Inference" section.

## Constitution Check

<!-- Placeholder constitution — loaded but 11 markers still unfilled, so no concrete governance constraints apply yet. -->

- Core Principles: Library-first not applicable (CLI app). Test-first applies to implementation; integration testing for LLM contract paths; observability via plain-text logging; versioning via MAJOR.MINOR.PATCH.
- No explicit violations found pending constitution content.

## Gates

- ERROR on unresolved clarifications — resolved: learner responses persisted as plain local JSON (no encryption/auth). See `checklists/requirements.md`.

## Phase 0: Research & Data Model (roadmap Phases P0–P5)

### research.md

<!-- Resolved in research.md; roadmap dependency drives Knowledge Base scope below. -->
- Local LLM orchestration patterns (Ollama client integration, model discovery, bundled-fallback behavior) in a PowerShell+Python hybrid.
- Free-response command-scoring strategies (pattern matching for shell commands like `podman pull`, multi-answer acceptance sets).
- Local persistence formats (JSON schema for progress, versioning).

### data-model.md — Knowledge Base scope per roadmap phases

<!-- Entities derived from roadmap: Knowledge Base (topics mapped to phases P0–P5), Session/Progress Record, Model Registry. -->
- **Phase mapping**: each topic entry tagged `phase ∈ {bridge, ml-literacy, mlops, k8s-ml-platform, llmops-gpu, portfolio}` so the explainer routes queries along the learner's path (roadmap P0→P5 flowchart).
- Beginner content emphasizes DevOps/platform fundamentals; experienced content emphasizes MLOps and LLMOps specifics such as GPU scheduling (`nvidia.com/gpu`) and RAG gateways — per spec Assumptions.

### Tasks (TDD order: tests → approve → red/green/refactor)

<!-- Populated post-research below. -->
- T-001: Knowledge base generator from RoadMap markdown (phase-tagged topics). [depends on data-model]
- T-002: LLM explainer for roadmap queries (Ollama REST via `[Net.HttpClient]`). [depends on research 1, roadmap P4 GPU/LLMOps specifics]
- T-003: Free-response challenge engine with multi-answer scoring. [depends on research 2]
- T-004: Progress persistence + resume across launches (plain JSON). [depends on research 3, spec FR-006]
- T-005: Interactive menu / overview (return-anywhere, level switch preserving progress). [spec User Story 4]
