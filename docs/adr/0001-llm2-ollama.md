# LLM2 uses local Ollama by default

Status: accepted

Context:

LLM2 orchestrator must work offline and avoid external model costs. Production may use remote models for non-sensitive workloads, but LLM2 must default to a local provider for privacy and latency reasons.

Decision:

Use Ollama `gpt-oss:latest` for LLM2; allow fallback only when `ATLAS_LLM2_ALLOW_FALLBACK=true` and fallback events are recorded in audit logs. Healthchecks and automated model-update procedures will be implemented to maintain model freshness.

Consequences:

- Positive: offline capability, lower external cost, deterministic execution in local infra.
- Negative: increased infra footprint (disk, memory), need for operational processes to update models, and added complexity around local provisioning.

Date: 2025-08-22

Notes:

- Implement a healthcheck endpoint for Ollama and emit Prometheus metrics (ollama_up: 1/0, ollama_response_ms).
- Document the fallback audit schema and where logs are stored (e.g., `infra/logs/audit.json` or centralized logging).
