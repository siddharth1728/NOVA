# Distributed Mobile-Host Architecture

## 1. Architectural Overview

NOVA Phase 03 transitions NOVA into a distributed computing architecture comprising:
1. **NOVA Windows Host Agent (`src/nova/host/`)**: Authoritative backend running on the user's primary Windows computer.
2. **NOVA iOS Control Center (`ios/NOVA/`)**: Native Swift 6 / SwiftUI handheld client running on the user's iPhone.
3. **NOVA Remote Protocol v1 (`src/nova/protocol/`)**: Typed JSON REST and WebSocket protocol enabling mutual discovery, authentication, desktop telemetry, screen capture, and goal dispatch.

```
┌────────────────────────────────────────────────────────┐
│                   iPhone (iOS 17+)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  NOVA Control Center (SwiftUI 6)                 │  │
│  │  - Dashboard & PC Hardware Gauges                │  │
│  │  - Natural Language Agent Goal Dispatch          │  │
│  │  - Live Desktop Screen Viewer                    │  │
│  │  - Real-Time Streaming Activity & Audit Feed     │  │
│  │  - Capability Matrix & Device Pairing Settings   │  │
│  └────────────────────────┬─────────────────────────┘  │
└───────────────────────────┼────────────────────────────┘
                            │  HTTP REST + WebSockets
                            │  (Encrypted Bearer Token)
┌───────────────────────────┼────────────────────────────┐
│                           ▼                            │
│               Windows PC (Authoritative Host)          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  NOVA Windows Host Service (Starlette / Uvicorn) │  │
│  │  - REST Endpoints (/api/v1/*)                    │  │
│  │  - WebSocket Hub (/ws/v1/events)                 │  │
│  │  - Ephemeral PIN Pairing Manager (6-Digit PIN)   │  │
│  │  - Device Trust Registry (.nova/devices.json)    │  │
│  │  - System Telemetry Provider (psutil)            │  │
│  │  - Desktop Screen Capture (Win32 GDI / Pillow)   │  │
│  │  - Power Controls (Win32 LockWorkStation)        │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │                            │
│                           ▼                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  NOVA Agent Runtime                              │  │
│  │  - Google Antigravity SDK Runtime                │  │
│  │  - 5-Tier Risk Model & Permission Engine         │  │
│  │  - Multi-Step Task Planner & Verification Engine │  │
│  │  - Append-Only Audit Trail & Memory Store        │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Responsibilities & Boundaries

| Component | Responsibility | Boundary & Security Constraint |
|---|---|---|
| **iOS App** | Presentation, query input, status display, emergency triggers | Read-only observation + goal dispatch. Cannot execute code locally. |
| **Windows Host** | Network interface, authentication, rate limiting, request validation | Validates all incoming tokens. Blocks remote shell execution. |
| **Control Layer** | Hardware telemetry, desktop frame grab, workstation lock | Native Win32 / OS calls. Safe fallbacks for headless/locked states. |
| **Agent Runtime** | LLM reasoning, multi-step planning, file tools, verification | Confined to `workspace_root`. Governed by risk taxonomy. |
