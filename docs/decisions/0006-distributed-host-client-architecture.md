# ADR 0006: Distributed Host-Client Architecture (iOS Control Center + Windows Authoritative Host)

## Status
Accepted (Phase 03)

## Context
NOVA began as a local workstation agent running solely on a single Windows machine.
Users need to observe, query, monitor, and emergency-lock their workstation remotely from a handheld device (iPhone) without being tethered to their desk.
However, running the agent reasoning runtime or attempting full workstation automation directly inside the iOS sandbox is technically impossible and architecturally undesirable.

## Decision
1. **Windows PC Remains Authoritative**:
   All filesystem access, tool executions, Antigravity AI reasoning, verification engines, and security policies execute exclusively on the Windows PC host.
2. **iPhone Acts as Thin Observation & Control Surface**:
   The native iOS app provides live telemetry, desktop screen viewing, goal dispatch, and emergency workstation locking via standard typed protocol envelopes.
3. **Transport Protocol**:
   A hybrid HTTP REST and WebSocket ASGI server built on Starlette and Uvicorn. REST handles point-in-time operations (pairing, status query, screen capture, emergency lock), while WebSockets (`/ws/v1/events`) stream live telemetry ticks and agent plan transitions.
4. **Strict Policy Separation**:
   Mobile clients cannot execute arbitrary shell scripts or bypass workspace containment. Remote commands undergo identical least-privilege checks as local commands, with high-risk operations (e.g. `run_command`) unconditionally prohibited over remote protocol.

## Consequences
- **Positive**: Clean separation of concerns; zero risk of mobile sandbox constraints impeding workstation agent power; security policies remain enforced in one authoritative location.
- **Negative**: Requires local network connectivity between iPhone and Windows PC (or secure VPN/tunnel for remote WAN access).
