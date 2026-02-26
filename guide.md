# Wolfclaw: Sovereign Intelligence Technical Guide

**Technical Designation**: Enterprise-Grade Sovereign Agentic Orchestrator (ESAO)

This document provides a comprehensive technical breakdown of the architectural philosophy and system internals of **Wolfclaw**.

---

## Section 1: The Essence of Wolfclaw

Wolfclaw is not merely a wrapper around Large Language Models. It is a **Sovereign Orchestration Environment**.

### The Three Pillars
1.  **Digital Autonomy**: Agents must be able to act within a defined trust boundary without constant human supervision.
2.  **Privacy of Soul**: The instructions (SOUL.md) and memories (MEMORY.md) that define an agent's identity must remain private and encrypted.
3.  **Cross-Provider Agnostic**: The system must treat LLMs as replaceable utilities, prioritizing local instances (Ollama) while maintaining high-performance bridges to cloud hardware (NVIDIA NIM).

---

## Section 2: Architectural Deep Dive

### 1. The Multiplexing Backend
Wolfclaw utilizes a FastAPI-based backend designed for low-latency command execution. It facilitates communication between:
- **The Web Dashboard**: A React/Tailwind SPA for visual orchestration.
- **The Telegram Worker**: An asynchronous proxy for mobile interaction.
- **WolfEngine**: The core LLM router that handles fallback logic and tool execution.

### 2. WolfEngine: The Heart of the System
The Engine is responsible for more than just text generation. It performs:
- **Dynamic Context Injection**: Merges Global Soul, Bot Personality, User Profile, and RAG data.
- **Agentic Tool Loop**: Interprets model intents and executes Python/Shell commands in real-time.
- **Reflection & Memory**: Post-conversation analysis to extract facts and update `MEMORY.md`.

### 3. Local Vault & Persistence
All sensitive data, including API keys and user credentials, is stored in a `Local Vault` (SQLite with opportunistic encryption). 
- **Workspaces**: Isolated logical containers for sets of bots and documents.
- **Sessions**: Token-based authentication for local and remote access.

---

## Section 3: Advanced Concepts

### Multi-Agent Interaction
The orchestration layer allows for specialized agents to coordinate on a single objective. 
- **Manager Agent**: Breaks down the task and assigns sub-problems.
- **Worker Agents**: Specialized bots (e.g., Coder, Researcher, Auditor) execute assigned tasks.
- **Synthesizer**: Combines results into a final, verified response.

### Soul Persistence Loop
Unlike stateless chatbots, Wolfclaw agents maintain state.
1.  **Ingestion**: Relevant memory chunks are fetched during the system prompt assembly.
2.  **Interaction**: The agent acts based on its evolving identity.
3.  **Reflection**: After completion, the agent reflects on the exchange and updates its local memory file.

---

## Section 4: Security & Isolation

- **Dockerized Runners**: (Optional) High-risk tasks are executed within transient containers.
- **Path Sanitization**: All file-system interactions are strictly gated to authorized directories.
- **RBAC**: Role-Based Access Control ensures that multi-tenant deployments maintain strict user isolation.

---
*End of Guide. Maintain the Professional Standard.*
<!-- Auth: Pravin A Mathew | Ref: PAM-Sovereign-Orchestration-v2 -->
