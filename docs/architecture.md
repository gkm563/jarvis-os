# JARVIS OS - System Architecture Specification

## Overview
JARVIS OS is an enterprise-grade, multi-agent AI operating layer designed to sit on top of Microsoft Windows (with future ports to macOS/Linux). It enables natural language and spoken voice control across desktop applications, web browsers, files, codebases, and productivity tools.

---

## Clean Architecture & DDD Layers

```
                          ┌───────────────────────────┐
                          │   Desktop UI & Voice HUD  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │  FastAPI REST & WS Layer  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   Multi-Agent DAG Planner │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │     Execution Manager     │
                          └──────┬─────────────┬──────┘
                                 │             │
             ┌───────────────────┴──┐       ┌──┴───────────────────┐
             │    Security Vault    │       │     Memory Engine    │
             │   (Permissions Gate) │       │  (SQLite + ChromaDB) │
             └───────────────────┬──┘       └──┬───────────────────┘
                                 │             │
    ┌────────────────────────────┴─────────────┴────────────────────────────┐
    │                       20 Specialized Domain Agents                     │
    │  Desktop | File | Browser | Coding | Vision | Voice | Email | Office  │
    └───────────────────────────────────────────────────────────────────────┘
```

### 1. `jarvis.core`
The innermost domain layer containing core models (`Plan`, `Step`, `AgentAction`, `ExecutionResult`), custom exceptions (`JarvisError`, `SecurityError`, `VaultError`), abstract interfaces (`BaseAgent`, `BaseSecurityVault`, `BaseLLMProvider`), and event bus channels.

### 2. `jarvis.security`
Implements zero-trust enterprise security guardrails:
- **AES-256 Vault (`vault.py`)**: Uses PBKDF2 HMAC-SHA256 key derivation for secret encryption at rest.
- **Permission Manager (`permissions.py`)**: Enforces granular scope checking per agent.
- **Sensitive Action Gate (`sensitive_gate.py`)**: Intercepts dangerous operations (banking, mass file deletion, credential updates) and demands explicit human confirmation tokens.
- **Anomaly Monitor (`anomaly.py`)**: Monitors agent invocation frequencies and sandboxes misbehaving processes.

### 3. `jarvis.memory`
Multi-tiered context store:
- **Short-Term (`short_term.py`)**: Volatile context store with TTL support.
- **Long-Term Relational (`long_term.py`)**: SQLAlchemy-backed SQLite/PostgreSQL store for user profiles, contacts, and audit execution logs.
- **Vector Memory (`vector_store.py`)**: ChromaDB semantic embedding engine for RAG over user task history.

### 4. `jarvis.brain`
AI Reasoning core featuring:
- **Universal LLM Provider (`llm_provider.py`)**: Multi-backend abstraction for OpenAI, Gemini, Anthropic, and local LLMs.
- **Task Planner (`planner.py`)**: Intent decomposition into Directed Acyclic Graphs (DAGs) with strict topological cycle detection.
- **Reflection Engine (`reflection.py`)**: Self-healing locator recovery when UI layouts change.

### 5. `jarvis.orchestration`
Async execution engine (`executor.py`) running DAG plans with retries, rollback tracking, and progress events.

### 6. `jarvis.agents`
20 specialized domain agents implementing `BaseAgent`.
