# NOVA: Personal AI Operating Layer

> **Phase 01: Foundational Architecture & Bootstrap**  
> Built natively on the **Google Antigravity** ecosystem.

NOVA is a local-first personal AI operating layer designed to safely understand natural-language goals, plan multi-step workflows, inspect project context, operate tools under strict human-in-the-loop policies, and maintain verified local state on the user's workstation.

---

## Current Status (v0.1.0)

Phase 01 establishes the production architecture and safety invariants. In this phase, **NOVA operates in strict, read-only mode** to guarantee that capabilities are deterministic, observable, testable, and secure by default.

### Implemented in Phase 01:
- **Typed Configuration & Secret Masking**: Robust settings powered by Pydantic Settings and `.env`, with automated secret scrubbing.
- **Tool Registry with 5-Tier Risk Model**: Formally categorizes all tools into `READ_ONLY`, `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
- **Least-Privilege Security Engine**: Restricts execution to read-only capabilities and strictly confines operations within the configured `workspace_root`.
- **Native Antigravity Policy Bridge**: Translates product policies into native `google.antigravity.hooks.policy.Policy` rules (`workspace_only`, `deny("run_command")`).
- **Local-First Memory Store**: Atomic, private local JSON persistence for user preferences, environment facts, task states, execution history, learned workflows, and project context.
- **Structured Observability & Audit Trail**: Append-only JSONL audit logging (`.nova/audit/audit.jsonl`) with automated secret redaction for API keys, tokens, and credentials.
- **Agent Lifecycle State Machine**: Enforces valid state transitions (`INITIALIZING` -> `READY` -> `PLANNING` -> `EXECUTING` -> `VERIFYING` -> `IDLE`).
- **Epistemic Discipline & Verification**: Enforces separation of `[OBSERVED]`, `[INFERRED]`, `[ASSUMED]`, and `[VERIFIED]` facts.
- **Antigravity SDK Runtime**: Encapsulates `google.antigravity.Agent` and `LocalAgentConfig` (v0.1.16).
- **Interactive & Diagnostic CLI**: Commands `nova info`, `nova check`, and `nova query "<prompt>"`.
- **Comprehensive Test Suite**: 41 unit and integration tests covering all subsystems.

---

## Installation & Setup

### Prerequisites
- Windows 10/11, macOS, or Linux
- Python `>= 3.10` (Tested on Python 3.11 and 3.14)
- [`uv`](https://docs.astral.sh/uv/) or `pip`

### Quickstart

1. **Clone or Navigate to Repository**:
   ```powershell
   cd c:\KaryaSetu
   ```

2. **Initialize Virtual Environment & Install**:
   ```powershell
   uv venv .venv
   uv pip install -e ".[dev]"
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and configure your API key (optional for local simulation):
   ```powershell
   Copy-Item .env.example .env
   ```

---

## CLI Usage

### System Information
Inspect runtime properties, version bindings, and security profiles:
```powershell
.venv\Scripts\nova info
```

### Subsystem Diagnostics
Run health checks across configuration, permissions, tools, audit, and memory:
```powershell
.venv\Scripts\nova check
```

### Workspace Query
Execute verified read-only workspace inspection:
```powershell
# Live Agent Inference (Requires GEMINI_API_KEY)
.venv\Scripts\nova query "List the important files in the current workspace"

# Local Verified Simulation (Offline, no external API key required)
.venv\Scripts\nova query "List the important files in the current workspace" --simulate
```

---

## Running Tests

Run the complete test suite with `pytest`:
```powershell
.venv\Scripts\pytest -v tests/
```

---

## Project Structure

```
NOVA/
├── pyproject.toml              # Project dependencies and packaging
├── .gitignore                  # Git hygiene and secret exclusion
├── .env.example                # Environment configuration template
├── README.md                   # Product documentation and quickstart
├── ARCHITECTURE.md             # In-depth architectural blueprint
├── SECURITY.md                 # Threat model and security architecture
├── ROADMAP.md                  # Staged multi-phase roadmap
├── CONTRIBUTING.md             # Development guidelines
│
├── src/nova/
│   ├── main.py                 # CLI entrypoint (info, check, query)
│   ├── errors.py               # Typed exception hierarchy
│   ├── config/
│   │   └── settings.py         # Pydantic settings with secret protection
│   ├── tools/
│   │   ├── categories.py       # Tool domain taxonomy
│   │   ├── metadata.py         # Tool descriptor & 5-tier risk model
│   │   └── registry.py         # Central tool registry & decorator
│   ├── security/
│   │   ├── risk.py             # Risk evaluation engine
│   │   ├── permissions.py      # Decision engine & workspace confinement
│   │   ├── approvals.py        # Human confirmation handlers
│   │   └── policies.py         # Antigravity native policy bridge
│   ├── memory/
│   │   ├── models.py           # Domain entities (Preference, Fact, Task, Record)
│   │   ├── interface.py        # Abstract MemoryStore interface
│   │   └── store.py            # LocalFileMemoryStore implementation
│   ├── observability/
│   │   ├── events.py           # Structured event taxonomy
│   │   ├── logging.py          # Structured logging & secret redaction
│   │   └── audit.py            # Append-only JSONL audit trail logger
│   ├── agent/
│   │   ├── prompts.py          # System instruction & epistemic rules
│   │   ├── lifecycle.py        # Session state machine
│   │   ├── configuration.py    # LocalAgentConfig synthesis
│   │   └── runtime.py          # NovaRuntime orchestrator
│   ├── skills/
│   │   └── workspace-explorer/ # Reference skill (SKILL.md)
│   └── subagents/
│       └── specs.py            # Subagent blueprints for future phases
│
├── tests/
│   ├── conftest.py             # Shared pytest fixtures
│   ├── unit/                   # 8 unit test suites (config, tools, security, memory, etc.)
│   └── integration/            # Runtime & Antigravity harness integration tests
│
└── docs/
    ├── decisions/              # Architecture Decision Records (ADRs)
    ├── security/               # Threat model specifications
    └── architecture/           # Deep-dive subsystem diagrams
```

---

## License

Apache-2.0. See repository LICENSE for details.
