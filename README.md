# NOVA: Personal AI Operating Layer

> **Phase 01: Foundational Architecture & Bootstrap**  
> Built natively on the **Google Antigravity** ecosystem.

NOVA is a local-first personal AI operating layer designed to safely understand natural-language goals, plan multi-step workflows, inspect project context, operate tools under strict human-in-the-loop policies, and maintain verified local state on the user's workstation.

---

## Current Status (v0.4.0)

Phase 04 establishes **real iOS productization, Windows host hardening, and end-to-end mobile connection resilience**:

### Core Capabilities:
- **Health & Readiness Endpoint**: `GET /api/v1/health` providing host state, agent state, versioning, uptime, and active task count.
- **Request Idempotency**: Host caches client request IDs to detect and safely deduplicate repeated mobile submissions.
- **Task Controller & Direct Cancellation**: Out-of-band task lifecycle coordinator supporting direct task aborts (`POST /api/v1/agent/tasks/{id}/cancel`) without LLM interpretation.
- **Hardened Device Authentication**: HMAC-SHA256 JWT validation with strict issuer (`nova-windows-host`), audience (`nova-ios-client`), device binding, and atomic Keychain storage.
- **Connection Lifecycle State Machine**: Full mobile state handling (`DISCONNECTED`, `CONNECTING`, `AUTHENTICATING`, `CONNECTED`, `DEGRADED`, `RECONNECTING`, `FAILED`) with exponential backoff reconnect.
- **Xcode & SPM Build Architecture**: Clean SPM (`Package.swift`) + XcodeGen (`project.yml`) + `Info.plist` with local network entitlements + GitHub Actions CI workflow on `macos-14`.
- **Live Latency & Gauges**: Dynamic roundtrip latency tracking and hardware resource gauges on iPhone Home screen.
- **Comprehensive Documentation**: Complete deployment guides for iOS, networking, pairing, Windows background services, and connection lifecycle.
- **Automated Test Suite**: 102 unit and integration tests passing with 100% success.

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
