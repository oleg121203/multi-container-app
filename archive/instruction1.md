Звісно, ось інструкція, підготовлена на основі вашого технічного завдання `ATLAS.md` та відформатована за шаблоном `instruction-template.md`.

-----

# Instruction.md for ATLAS Project Implementation

## 1\. Context/Background

  - **Project Description:** The task is to implement **ATLAS**, a multi-agent Large Language Model (LLM) system. The system is designed for complex task orchestration, featuring persistent memory, modular tools, and robust security monitoring.
  - **Relevant Background:** The architecture involves three core LLM agents with distinct roles: LLM1 for user interaction and memory (RAG), LLM2 for local task orchestration (Ollama), and LLM3 for security oversight (Falco). A key component is the **MCP Hub**, a modular system for integrating tools like Playwright, macOS automation, and Text-to-Speech (TTS) as containerized services.
  - **Current State:** This is a new project. The initial setup is described in a conceptual `docker-compose` format, which needs to be migrated to a more robust Kubernetes environment.
  - **Links to Relevant Documents:** The primary source of truth is the `ATLAS.md` technical specification.

## 2\. Goals and Objectives

  - **Primary Goal:** To build a functional Minimum Viable Product (MVP) of the ATLAS system by implementing its core infrastructure, agent logic, and key features in sequential phases.
  - **Expected Outcomes:**
    1.  A Kubernetes-deployed application with three distinct, communicating LLM agents.
    2.  A functional RAG-based long-term memory system using a vector database.
    3.  A secure and isolated environment for browser and OS automation.
    4.  A modular tool integration system (MCP Hub) with dynamic selection capabilities.
    5.  A dynamic agent team constructor with user approval gates.
  - **Success Criteria:** Successful completion of all phases, passing all specified tests, and meeting the acceptance criteria outlined in `ATLAS.md`.

## 3\. Specific Requirements

The implementation is broken down into four sequential phases. Each phase concludes with a mandatory testing and validation stage.

-----

### **Phase 1: Infrastructure Foundation**

This phase focuses on setting up the Kubernetes environment and the essential data and observability services.

  - **`INF-01`:** Implement `docker-compose` configurations for **Qdrant** (or Milvus) and **Redis**, ensuring they use persistent volumes for data storage.
  - **`INF-02`:** Use **Kompose** to convert the complete `docker-compose` setup into Kubernetes manifests. Manually refine the generated manifests to:
      - Convert database deployments to `StatefulSet`.
      - Add `PersistentVolumeClaim` templates for storage.
      - Implement readiness and liveness probes for all services.
      - Define resource requests and limits (`cpu`, `memory`).
      - Configure node affinity/anti-affinity rules for high availability.
  - **`OBS-01`:** Deploy **Prometheus** and **Grafana** into the cluster. Create an initial Grafana dashboard to monitor basic cluster and pod health.
  - **`OPS-01` (Partial):** Create Kubernetes Secrets for all required API keys and credentials. Set up initial RBAC roles with the principle of least privilege.
  - **Testing and Validation:**
      - **Unit Tests:** Create configuration validation tests (e.g., linting K8s manifests).
      - **Integration Tests:** Write scripts to verify that core services (agents, databases) can connect to each other within the cluster.
      - **CI Pipeline:** Set up an initial CI pipeline that automatically lints and validates the Kubernetes manifests on each commit.

-----

### **Phase 2: Core Agent and Memory Implementation**

This phase brings the primary agents to life and establishes their core functionalities.

  - **`MEM-01`:** Implement the RAG memory layer for LLM1. This includes:
      - Logic for text chunking, embedding generation, and indexing into Qdrant.
      - A search function to retrieve relevant context based on user queries.
      - Integration with Redis for session-based short-term memory (semantic cache).
  - **`CFG-01`:** Create a generic LLM provider abstraction layer for LLM1 and LLM3. It must support OpenAI, Mistral, Gemini, and Ollama with a unified interface and a configurable fallback chain (e.g., `openai -> gemini -> ollama`).
  - **`ORC-01`:** Implement LLM2 using **AutoGen** or **MetaGPT**.
      - Integrate a local **Ollama** instance as the primary model provider.
      - Develop the "Linear" tool, enabling the agent to create and update issues via the Linear GraphQL API.
  - **`CFG-02`:** Enforce a strict policy for LLM2 to use the local Ollama model (`gpt-oss:latest`). Implement a health check and a controlled fallback mechanism that is disabled by default (`ATLAS_LLM2_ALLOW_FALLBACK=false`) and logs any deviations.
  - **Testing and Validation:**
      - **Unit Tests:** Test the RAG indexing/retrieval logic, the LLM provider abstraction, and the Linear tool's GraphQL mutations.
      - **Integration Tests:** Verify that LLM1 correctly uses the RAG layer and that LLM2 can successfully connect to the local Ollama instance and the external Linear API.
      - **E2E Tests:** Create an end-to-end test flow: "User submits a request -\> LLM1 processes it using context from RAG -\> LLM2 receives the task and creates an issue in Linear."
      - **CI/CD:** Extend the CI pipeline to run all unit and integration tests automatically.

-----

### **Phase 3: Automation, Security, and Modular Tools (MCP Hub)**

This phase focuses on implementing advanced automation capabilities and the security monitoring agent.

  - **`MCP-01`:** Build the initial **MCP Hub**. Add containerized MCP servers for Playwright and general automation, making them discoverable via environment variables (`ATLAS_MCP_SERVERS`).
  - **`GUI-01`:** Configure a secure environment for running Playwright, preferably using isolated containers (like Apple containers on macOS) or a browser workspace solution like Kasm.
  - **`SEC-01`:** Implement LLM3.
      - Install **Falco** in the cluster and configure it to stream security events.
      - Connect LLM3 to the Falco event stream.
      - Implement logic for LLM3 to analyze events and trigger automated responses via the Kubernetes API (e.g., `cordon node`, `delete pod`).
  - **`MCP-05` & `MCP-06`:** Integrate the **TTS MCP** (`blacktop/mcp-tts`).
      - Configure multiple TTS providers (e.g., OpenAI, Google, ElevenLabs) and a local **Coqui TTS** server as a fallback.
      - Implement voice mapping to specific agents (`ATLAS_TTS_AGENT_VOICE_LLM1=...`).
  - **`MCP-02` & `MCP-03`:** Implement the "two MCPs for macOS management" concept (Automation MCP and macOS Automator MCP). Implement a telemetry system that exports metrics (latency, success rate) to Prometheus and a policy for LLM2 to automatically select the best tool for a given task based on historical performance.
  - **`MCP-04`:** Assemble and document the "Base MCP Package" as defined in `ATLAS.md`.
  - **Testing and Validation:**
      - **Unit Tests:** Test Falco event parsing, TTS provider logic, and MCP tool selection policies.
      - **Integration Tests:** Verify that LLM2 can successfully call each configured MCP server. Test the TTS fallback mechanism by simulating a primary provider failure.
      - **E2E Tests:**
        1.  "User asks to take a screenshot of a website -\> LLM2 uses the Playwright MCP to perform the action."
        2.  "A simulated high-priority Falco event is generated -\> LLM3 detects it and executes a predefined K8s API action."
        3.  "An agent generates a response -\> The TTS MCP successfully converts it to audio using a designated voice."
      - **CI/CD:** Add E2E automation tests to the pipeline.

-----

### **Phase 4: Dynamic Teams and User Interface**

This final MVP phase implements advanced agent collaboration and provides a basic interface for interaction.

  - **`TEAM-01` & `TEAM-02`:** Implement the **Agent Registry**.
      - Create CRUD APIs for managing agents and their configurations (model, skills, API keys via K8s Secrets).
      - Implement a system for defining team roles and personas from YAML templates.
  - **`TEAM-03`:** Build the **Dynamic Team Constructor**.
      - Use AutoGen/MetaGPT to analyze a task's intent and dynamically assemble a team of agents from the registry.
      - Implement a "human-in-the-loop" gate, requiring user approval before a proposed team begins execution.
  - **`TEAM-04` & `TEAM-05`:** Integrate with Orkes for long-running workflows and create a Grafana dashboard to track team performance metrics (cost, duration, success rate).
  - **`UI-01`:** After backend contracts are stable, develop a minimal, **functional** web interface. This UI must be fully connected to the backend APIs and MCPs, with no mock data or demo modes.
  - **Testing and Validation:**
      - **Unit Tests:** Test the logic for agent registration and dynamic team assembly.
      - **Integration Tests:** Verify the interaction between the Team Constructor, Agent Registry, and AutoGen.
      - **E2E Tests:**
        1.  "User defines several agents in the registry -\> User submits a complex multi-step task -\> System proposes a team with roles -\> User approves -\> Team executes the task using MCP tools."
        2.  **`UI-02`:** Create a suite of frontend E2E tests using Playwright that simulates user interactions in the web UI and validates the full-loop behavior against the live backend.
      - **CI/CD:** Integrate the frontend E2E test suite into the main CI/CD pipeline, running it against a staging environment.

-----

## 4\. Constraints and Guidelines

  - **Technical Constraints:**
      - **LLM2:** Must strictly use a local **Ollama** model (`gpt-oss:latest`) by default. Remote model usage is an explicit, logged exception.
      - **Migration:** The initial migration from `docker-compose` to Kubernetes **must** use **Kompose**, with subsequent manual refinement.
  - **Design Patterns:**
      - **Tooling:** All agent tools (Playwright, Automators, TTS, etc.) must be exposed as containerized, modular services via the **MCP Hub**.
  - **Security Requirements:**
      - All secrets (API keys, credentials) must be managed via **Kubernetes Secrets**.
      - **RBAC** must be configured with the principle of least privilege.
      - Browser automation via Playwright must run in a **highly isolated environment**.
  - **Frontend Policy:** A web UI should only be developed *after* backend APIs are stable. Any UI built must be fully functional and interact with the real backend, without mocks.

## 5\. Format Preferences

  - **Programming Language:** Python is highly recommended for the agent and AI-related services due to the ecosystem (AutoGen, LangChain, etc.).
  - **Code Structure:** The codebase should be modular, with clear separation between agent logic, tool adapters (MCP clients), and infrastructure configuration.
  - **Documentation:** A `README.md` must be provided with clear setup and deployment instructions. Grafana dashboards should be exportable as JSON files.
  - **File Organization:** All Kubernetes manifests should be located in a dedicated `k8s/` directory.

## 6\. Examples

  - **MCP Hub `docker-compose` Snippet:**
    ```yaml
    services:
      mcp-playwright:
        image: ghcr.io/example/playwright-mcp:latest
        ports: ["4001:4001"]
        environment:
          - MCP_PORT=4001
      mcp-automation:
        image: ghcr.io/example/automation-mcp:latest
        ports: ["4002:4002"]

      llm2-orchestrator:
        # ...
        environment:
          - ATLAS_MCP_SERVERS=playwright,automation
          - ATLAS_MCP_PLAYWRIGHT_URL=http://mcp-playwright:4001
          - ATLAS_MCP_AUTOMATION_URL=http://mcp-automation:4002
    ```
  - **TTS Service `docker-compose` Snippet:**
    ```yaml
      mcp-tts:
        image: ghcr.io/blacktop/mcp-tts:latest
        ports: ["4004:4004"]
        environment:
          - MCP_PORT=4004
          - ATLAS_TTS_PROVIDERS=say_tts,openai_tts,coqui_tts
          - COQUI_TTS_BASE_URL=http://coqui-tts:5002
          # ... other provider API keys
        depends_on:
          - coqui-tts

      coqui-tts:
        image: ghcr.io/coqui-ai/tts-cpu:latest
        ports: ["5002:5002"]
    ```

## 7\. Priority and Timeline

  - **Priority:** High. This is a foundational project.
  - **Timeline:** The project timeline is defined by the sequential completion of the four phases outlined above. Each phase should be considered a milestone.

## 8\. Additional Notes

  - **Expected Artifacts:**
      - `k8s/` directory with all Kubernetes manifests.
      - Source code for all agents, MCP clients, and other services.
      - `README.md` with comprehensive setup instructions.
      - Exported JSON files for Grafana dashboards.
  - This instruction is a direct interpretation of the `ATLAS.md` technical specification, designed to be executed by a coding agent. The focus is on a phased, test-driven implementation.