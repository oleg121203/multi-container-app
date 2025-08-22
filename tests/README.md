# Tests scaffold

This folder is a placeholder for test code. Suggested suites:

- Python (pytest): RAG unit tests (chunking, embeddings, retrieval)
- Python/JS: LLM provider abstraction + fallback chain tests
- Integration: LLM1↔RAG, LLM2↔Ollama health, Linear GraphQL client
- Security: Falco event parsing → LLM3 decision mock
- E2E: user → LLM1 (RAG) → LLM2 (plan + Linear)

Add your preferred language test runner configs (pytest.ini, package.json scripts, etc.).
