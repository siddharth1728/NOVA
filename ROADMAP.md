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

## Phase 03: Distributed Personal Computing Architecture (COMPLETED)
- [x] Authoritative Windows NOVA Host service (`src/nova/host/`) using Starlette ASGI and Uvicorn.
- [x] NOVA Remote Protocol v1 (`src/nova/protocol/`) for typed JSON REST and real-time WebSockets (`/ws/v1/events`).
- [x] Ephemeral 6-digit PIN device onboarding (`nova host pair-code`) with 300s TTL and single-use consumption.
- [x] Persistent Device Trust Registry (`.nova/devices.json`) and HMAC-SHA256 JWT bearer token issuance.
- [x] Instant host device revocation (`nova host revoke <device_id>`).
- [x] Live hardware telemetry provider (`psutil`) reading CPU, RAM, disk, OS version, and host uptime.
- [x] Desktop screen capture provider (Win32 GDI / Pillow) with safe diagnostic canvas frame fallback for detached sessions.
- [x] Emergency workstation lock provider (`LockWorkStation`).
- [x] Capability discovery matrix (`GET /api/v1/capabilities`) strictly prohibiting remote shell execution.
- [x] Remote agent goal dispatch with empirical verification and append-only audit logging.
- [x] Native iOS 18 Control Center (`ios/NOVA/`) with 5-tab SwiftUI interface (Dashboard, Agent, Computer, Activity, Settings).
- [x] Comprehensive test suite (93 total tests passing, 100% success).

---

## Phase 04: Real iOS Productization & Host Hardening (COMPLETED)
- [x] Service health endpoint (`GET /api/v1/health`) exposing operational state, versioning, and active tasks.
- [x] Request idempotency cache deduplicating repeated mobile submissions.
- [x] Direct task cancellation controller (`POST /api/v1/agent/tasks/{id}/cancel`) bypassing LLM reasoning.
- [x] Hardened JWT authentication validating issuer (`nova-windows-host`), audience (`nova-ios-client`), and device binding.
- [x] Connection lifecycle state machine (`NovaAppModel`) with automatic exponential backoff reconnect.
- [x] Dynamic roundtrip latency tracking and live hardware telemetry gauges on iPhone.
- [x] XcodeGen (`project.yml`), Swift Package (`Package.swift`), `Info.plist` with local network entitlements, and asset catalogs.
- [x] GitHub Actions CI workflow (`.github/workflows/ios-build.yml`) for automated macOS runner build verification.
- [x] Comprehensive mobile and Windows deployment documentation.
- [x] 102 automated tests passing with 100% success rate.

---

## Phase 05: Interactive Computer & Desktop Control (NEXT)
- [ ] Direct mouse control (cursor move, click, double click, right click, scroll).
- [ ] Keyboard input simulation (type text, hotkeys, key combinations).
- [ ] Active window inspection and focus management.
- [ ] Low-latency visual streaming / delta compression for interactive desktop view.
- [ ] Safety guardrails and emergency hardware-interrupt release.
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
