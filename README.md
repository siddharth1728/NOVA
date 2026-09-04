# NOVA: Personal AI Operating Layer

> **Phase 01: Foundational Architecture & Bootstrap**  
> Built natively on the **Google Antigravity** ecosystem.

NOVA is a local-first personal AI operating layer designed to safely understand natural-language goals, plan multi-step workflows, inspect project context, operate tools under strict human-in-the-loop policies, and maintain verified local state on the user's workstation.

---

## Current Status (v0.3.0)

Phase 03 transforms NOVA into a **distributed personal AI computing system**, pairing a native **iOS Control Center** running on iPhone with an authoritative **Windows NOVA Host** running on the user's PC.

### Core Capabilities:
- **Distributed Host-Client Architecture**: Windows PC remains authoritative execution host; iPhone acts as thin observation, query, and emergency control surface.
- **NOVA Remote Protocol v1**: Clean typed protocol schemas (`models.py`) supporting HTTP REST and real-time WebSockets (`/ws/v1/events`).
- **Device Pairing & Session Trust**: Ephemeral 6-digit PIN onboarding (`nova host pair-code`), persistent device trust registry (`.nova/devices.json`), HMAC-SHA256 JWT bearer tokens, and immediate device revocation (`nova host revoke`).
- **Windows Control Layer**: Live hardware telemetry (`psutil`), desktop screen capture (Win32 GDI / Pillow) with headless/locked safe fallback, and remote workstation lock (`LockWorkStation`).
- **Remote Agent Goal Dispatch**: Dispatches natural language tasks from mobile to `NovaRuntime` with empirical verification and append-only audit logging.
- **Strict Remote Security**: High-risk arbitrary shell execution (`run_command`, PowerShell) is strictly blocked over remote protocol.
- **Native iOS 18 Application (`ios/NOVA/`)**: Pure Swift 6 / SwiftUI application with 5-tab interface: Dashboard Gauges, Agent Query Dispatch, Desktop Screen Viewer, Live Activity Feed, and Device Settings.
- **Transactional Workspace Operations**: Full Phase 02 capability preserved (multi-step planning, atomic file operations, LIFO rollback).

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

### Windows Host Service (Phase 03)
Start the background ASGI host service on your Windows PC:
```powershell
.venv\Scripts\nova host start --port 8000
```

Generate an ephemeral 6-digit PIN code to pair your iPhone:
```powershell
.venv\Scripts\nova host pair-code
```

Inspect or revoke paired mobile devices:
```powershell
.venv\Scripts\nova host devices
.venv\Scripts\nova host revoke <device_id>
```

---

## iOS Control Center (`ios/NOVA/`)

The native iOS client allows you to monitor and control your Windows PC directly from your iPhone.
See [docs/ios/build-and-signing.md](docs/ios/build-and-signing.md) for full macOS/Xcode build instructions, entitlements, and TestFlight deployment guidelines.

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
# NOVA
