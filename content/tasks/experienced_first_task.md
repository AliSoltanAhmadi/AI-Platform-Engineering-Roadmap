# Experienced Lesson — Operating LLM Inference

LLMOps applies production practices to large language models. An inference server loads a model artifact from a registry and exposes an API. GPU scheduling assigns accelerator capacity to that server while preventing workloads from competing unpredictably.

The first stage uses vLLM's OpenAI-compatible server. Production follow-up work includes health checks, model versioning, capacity limits, and observability.

Prerequisites: Kubernetes scheduling, GPU drivers, and container registries.
