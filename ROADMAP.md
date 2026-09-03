# NOVA Multi-Phase Roadmap

NOVA is evolving systematically through disciplined phases. Each phase expands capabilities only after safety, observability, and deterministic verification have been proven in the preceding phase.

---

## Phase 01: Foundational Architecture & Bootstrap (COMPLETED)
- [x] Environment and Antigravity SDK binding (`google-antigravity` v0.1.16).
- [x] Typed configuration system with Pydantic and secret masking.
- [x] Tool Registry with 5-tier risk taxonomy (`READ_ONLY`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- [x] Least-privilege security engine & workspace boundary confinement.
- [x] Native Antigravity policy bridge (`workspace_only`, `deny("run_command")`).
- [x] Local-first file-based memory store (`UserPreference`, `EnvironmentFact`, `TaskState`, `ExecutionRecord`, `LearnedWorkflow`, `ProjectContext`).
- [x] Structured observability and append-only JSONL audit trail with secret scrubbing.
- [x] Session lifecycle state machine and epistemic verification loop.
- [x] Functional CLI (`nova info`, `nova check`, `nova query`).
- [x] Unit and integration test suite (42 tests).

---

## Phase 02: Controlled Workspace Mutations & Multi-Step Planning (COMPLETED)
- [x] Six controlled mutation tools (`create_directory`, `create_file`, `edit_file`, `rename_file`, `move_file`, `copy_file`).
- [x] Robust canonical path confinement with Windows case-insensitivity and traversal blocking.
- [x] Transaction & LIFO Rollback Manager with automated snapshot backups under `.nova/backups/`.
- [x] Concurrency and stale-file conflict detection (`FILE_CHANGED_SINCE_PLAN`).
- [x] Multi-step task planner with topological dependency sorting.
- [x] Cryptographic plan hashing (SHA-256) and runtime plan drift prevention (`PlanDriftError`).
- [x] Empirical verification engine asserting direct filesystem state.
- [x] CLI commands: `nova plan` (pure dry-run) and `nova execute` (transactional apply with approval).
- [x] Comprehensive test suite (74 tests passing, 0 failing).

---

## Phase 03: Specialized Subagent Activation & Delegation (NEXT)
- [ ] Activation of static subagents via Antigravity `SubagentConfig`.
- [ ] Planner Subagent: Autonomous goal decomposition.
- [ ] Researcher Subagent: Document synthesis and web research.
- [ ] Coder Subagent: Automated implementation and refactoring.
- [ ] Verifier Subagent: Automated test execution and post-condition checks.

---

## Phase 04: Structured Browser Automation & Model Context Protocol (MCP)
- [ ] Antigravity browser automation integration for web workflows.
- [ ] Integration of standard MCP servers (`McpStdioServer`, `McpStreamableHttpServer`).
- [ ] MCP tool discovery, risk classification, and policy enforcement.

---

## Phase 05: Sandboxed Terminal & Developer Operations
- [ ] Gated execution of shell commands within containerized or sandboxed environments.
- [ ] Git workflow automation (branching, commits, pull requests).
- [ ] Build and test runner operations with automated failure recovery.

---

## Phase 06: Semantic Memory & Knowledge Graph
- [ ] Local vector embedding store (Chroma or sqlite-vec) for semantic retrieval.
- [ ] Project architecture knowledge graph.
- [ ] Long-term user preference and workflow recall across sessions.

---

## Phase 07: Desktop Automation & Proactive Assistance
- [ ] Verified computer control and OS accessibility automation.
- [ ] Proactive triggers (file change watchers, scheduled cron jobs).
- [ ] Voice and multimodal interface integration.
