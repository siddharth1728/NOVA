# NOVA: Personal AI Operating Layer

> **Phase 01: Foundational Architecture & Bootstrap**  
> Built natively on the **Google Antigravity** ecosystem.

NOVA is a local-first personal AI operating layer designed to safely understand natural-language goals, plan multi-step workflows, inspect project context, operate tools under strict human-in-the-loop policies, and maintain verified local state on the user's workstation.

---

## Current Status (v0.2.0)

Phase 02 elevates NOVA into a **controlled workspace operator**, enabling safe, reversible, multi-step mutations within the configured workspace.

### Core Capabilities:
- **Six Workspace Mutation Tools**: `create_directory`, `create_file`, `edit_file`, `rename_file`, `move_file`, `copy_file`.
- **Atomic File Operations**: Automatic sibling temp file creation and `os.replace` replacement on Windows NTFS and POSIX.
- **Transaction & LIFO Rollback Manager**: Atomic groups of operations with automated snapshot backups under `.nova/backups/`. Reverses operations in strict LIFO order upon failure.
- **Stale-State Protection**: Detects conflicting modifications made since planning (`FILE_CHANGED_SINCE_PLAN`).
- **Multi-Step Task Planning**: Dependency-ordered milestone decomposition with Kahn's algorithm cycle detection.
- **Cryptographic Plan Integrity**: Deterministic SHA-256 plan hashing preventing runtime argument or tool drift (`PlanDriftError`).
- **Empirical Verification**: Direct filesystem checks on disk (existence, absence after move/rename, SHA-256 hash preservation).
- **Interactive CLI Experience**: `nova plan` for pure dry-run inspection and `nova execute` for transactional apply with user confirmation.
- **Automated Test Suite**: 74 unit and integration tests passing with 100% success.

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
   Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

---

## CLI Usage

### System Information & Diagnostics
```powershell
.venv\Scripts\nova info
.venv\Scripts\nova check
```

### Multi-Step Planning (Dry-Run Mode)
Inspect workspace and generate a structured plan without making any modifications:
```powershell
.venv\Scripts\nova plan "Create a Python project structure called demo-service with src/ and README.md"
```

### Transactional Plan Execution
Review plan, authorize with confirmation gate, execute mutations, and verify empirically:
```powershell
.venv\Scripts\nova execute "Create a Python project structure called demo-service with src/ and README.md"
```

### Verified Read-Only Query
```powershell
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
