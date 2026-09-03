# NOVA Architecture Blueprint

This document details the software architecture, design principles, and component interactions of **NOVA** (v0.1.0).

---

## 1. System Overview & Component Hierarchy

NOVA is architected as a layered runtime decoupling the user-facing product domain from the underlying model orchestration backend.

```
+-------------------------------------------------------------+
|                      User / CLI Layer                       |
|           (nova info, nova check, nova query)               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     NOVA Runtime Core                       |
|   +---------------------+        +----------------------+   |
|   |  Lifecycle State    |        | Epistemic Verifier   |   |
|   |  Machine            |        | (Observed vs Assumed)|   |
|   +---------------------+        +----------------------+   |
+-------------------------------------------------------------+
         |                       |                     |
         v                       v                     v
+-----------------+     +-----------------+   +---------------+
| Security Engine |     |  Memory Store   |   | Observability |
| - Confinement   |     | - Preferences   |   | - JSONL Audit |
| - 5-Tier Risk   |     | - Facts & Tasks |   | - Redaction   |
| - Approval Gate |     | - Workflows     |   | - Telemetry   |
+-----------------+     +-----------------+   +---------------+
         |
         v
+-------------------------------------------------------------+
|                  Antigravity Policy Bridge                  |
|        (workspace_only, confirm_run_command, allow)         |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|             Google Antigravity SDK Runtime                  |
|    (Agent, LocalAgentConfig, CapabilitiesConfig, Hooks)     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                Local Harness & Tool Execution               |
|            (localharness.exe via stdin/IPC/WS)              |
+-------------------------------------------------------------+
```

---

## 2. Component Specifications

### 2.1 Configuration Subsystem (`nova.config`)
- Powered by `pydantic-settings.BaseSettings`.
- Loads settings from environment variables (`NOVA_*`), `.env` files, or programmatic kwargs.
- Secrets are encapsulated in `pydantic.SecretStr`, ensuring credentials are masked as `********` across loggers and representations.
- Safe serialization via `NovaSettings.safe_dump()`.

### 2.2 Tool Registry & 5-Tier Risk Taxonomy (`nova.tools`)
Every tool exposed to NOVA is bound to a typed `ToolMetadata` record:
- **`READ_ONLY`**: Pure inspection (e.g. `list_directory`, `view_file`, `find_file`).
- **`LOW`**: Minor non-destructive operations (e.g. `search_web`, `ask_question`).
- **`MEDIUM`**: Reversible mutations within workspace (e.g. `create_file`, `edit_file`).
- **`HIGH`**: Irreversible modifications or external transfers.
- **`CRITICAL`**: Host execution, arbitrary shells (`run_command`), privileged processes.

Custom tools are registered via `@nova_tool` decorator with automated schema inference.

### 2.3 Security Engine & Workspace Confinement (`nova.security`)
- **Confinement Checking**: `check_workspace_containment()` resolves target paths against `workspace_root`, normalizing Windows case insensitivity and blocking directory traversal (`../`) or absolute path escapes.
- **Permission Decision Engine**: Evaluates `(tool, args)` against the active `SecurityMode`:
  - `STRICT`: Only `READ_ONLY` tools permitted; write/terminal operations denied.
  - `STANDARD`: `READ_ONLY` and `LOW` allowed; `MEDIUM` requires approval; `HIGH`/`CRITICAL` denied.
  - `PERMISSIVE`: Experimental configuration.
- **Antigravity Policy Bridge**: Translates product decisions into native `google.antigravity.hooks.policy.Policy` objects (`workspace_only`, `deny()`, `ask_user()`).

### 2.4 Local-First Memory Subsystem (`nova.memory`)
- Implemented via `LocalFileMemoryStore` adhering to `MemoryStore` ABC.
- Zero network exposure: all facts, preferences, and execution logs persist in local JSON files under `.nova/memory/`.
- Domain models:
  - `UserPreference`: Coding style, language, and tool choices.
  - `EnvironmentFact`: Verified machine properties.
  - `TaskState`: Active goal and sub-step progress.
  - `ExecutionRecord`: Historical outcome log.
  - `LearnedWorkflow`: Repeatable procedural knowledge.
  - `ProjectContext`: Architecture and repository domain metadata.

### 2.5 Structured Observability & Audit Trail (`nova.observability`)
- Append-only JSONL log at `.nova/audit/audit.jsonl`.
- **Secret Scrubbing**: Pre-write sanitization with `redact_sensitive_data()` strips API keys (`AIzaSy...`), Bearer tokens, and confidential dictionary keys.
- **Telemetry Hook**: `AuditPostToolCallHook` intercepts Antigravity SDK tool completions and logs execution metadata (duration, success, inputs, results) in real time.

### 2.6 Agent Lifecycle & Verification Loop (`nova.agent`)
- **State Machine**: Enforces strictly valid state transitions:
  `INITIALIZING` -> `READY` -> `PLANNING` -> `EXECUTING` -> `VERIFYING` -> `IDLE` (or `FAILED`).
- **Epistemic Discipline**: NOVA prompt enforces explicit tagging:
  - `[OBSERVED]`: Directly witnessed from tools or files.
  - `[INFERRED]`: Deductions drawn from observed evidence.
  - `[ASSUMED]`: Hypotheses awaiting empirical proof.
  - `[VERIFIED]`: Proven outcomes matching post-conditions.
- **Post-Action Verification**: `verify_outcome()` validates that claims regarding files or state mutations are backed by empirical tool events.

### 2.7 Transaction & Rollback Subsystem (`nova.transactions`)
- **Atomic Operations**: All file mutations write through temporary files with atomic `os.replace` semantics.
- **LIFO Rollback**: If an operation fails mid-transaction, previously completed mutations are reverted in strict reverse order (Last-In-First-Out).
- **Snapshot Backups**: Pre-mutation file contents are preserved under `.nova/backups/<tx_id>/`.
- **Precondition & Stale-State Protection**: Validates SHA-256 pre-hashes before applying edits; conflicting concurrent changes raise `FILE_CHANGED_SINCE_PLAN`.
- **Integrity Alarm**: If rollback itself fails, `RollbackFailedError` is raised with `ROLLBACK_FAILED` state to ensure no silent corruption.

### 2.8 Multi-Step Planning & Plan Integrity (`nova.planning`)
- **Dependency-Ordered Plans**: `TaskPlanner` synthesizes discrete, dependency-ordered plans (`PlanStep`) with topological cycle detection.
- **Deterministic Plan Hashing**: SHA-256 digest of canonical plan contents binds human approval directly to the execution envelope.
- **Plan Drift Guard**: `PlanExecutor` re-verifies the plan hash prior to execution; any parameter drift raises `PlanDriftError` and halts execution.

### 2.9 Empirical Verification Engine (`nova.verification`)
- **Direct Filesystem Invariants**: Validates actual disk state rather than tool return codes:
  - Verifies presence of created files and directories.
  - Verifies absence of sources following moves and renames.
  - Verifies content hashes against expected postconditions.
  - Validates clean restoration of pre-transaction state during rollback.

---

## 3. Skills and Subagent Extensibility

- **Skills**: Fully aligned with the Antigravity skill layout (`<skill_dir>/SKILL.md`). `workspace-explorer` provides a reference implementation.
- **Subagents**: Defined by `SubagentBlueprint` specifications (Planner, Researcher, Coder, Browser Operator, Computer Operator, Verifier, Security Reviewer, Document Specialist). Blueprints map directly to native `SubagentConfig`.

