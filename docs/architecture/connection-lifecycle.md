# Mobile-Host Connection Lifecycle & Reconnection State Machine

## 1. Connection Lifecycle State Machine

The native iOS client (`NovaAppModel`) maintains a deterministic connection state machine:

```
                  ┌──────────────┐
                  │ DISCONNECTED │
                  └──────┬───────┘
                         │ startConnection()
                         ▼
                  ┌──────────────┐
                  │  CONNECTING  │ ──> Health check: GET /api/v1/health
                  └──────┬───────┘
                         │ (200 OK)
                         ▼
                  ┌────────────────┐
                  │ AUTHENTICATING │ ──> Token check: GET /api/v1/status
                  └──────┬─────────┘
                         │ (200 OK)
                         ▼
                  ┌──────────────┐
       ┌─────────>│  CONNECTED   │ ──> WebSocket connected (/ws/v1/events)
       │          └──────┬───────┘     Periodic telemetry poll (every 3s)
       │                 │
       │                 │ Heartbeat timeout / Network loss
       │                 ▼
       │          ┌──────────────┐
       │          │   DEGRADED   │
       │          └──────┬───────┘
       │                 │ Exponential backoff (1s, 2s, 4s, ... 15s)
       │                 ▼
       │          ┌──────────────┐
       └──────────│ RECONNECTING │ ──> Health check + token restore
                  └──────┬───────┘
                         │ Max failures / Invalid token
                         ▼
                  ┌──────────────┐
                  │    FAILED    │
                  └──────────────┘
```

---

## 2. State Definitions

| State | Description | UI Manifestation |
|---|---|---|
| `DISCONNECTED` | Client is uninitialized or unconfigured. | Red dot, "Offline" label. |
| `CONNECTING` | Initial TCP connection & health endpoint check. | Blue dot, "Connecting" label. |
| `AUTHENTICATING` | Validating JWT bearer token against host registry. | Blue dot, "Authenticating" label. |
| `CONNECTED` | Both HTTP REST and WebSocket stream active. | Green dot, "Online" label + latency ms. |
| `DEGRADED` | REST active but WebSocket dropped, or high latency. | Orange dot, "Degraded" label. |
| `RECONNECTING` | Automatic backoff attempt following network disruption. | Blue dot, "Reconnecting" label. |
| `FAILED` | Host unreachable or token revoked by host. | Red dot, "Failed" label + error banner. |

---

## 3. Reconnect Protocol & State Resynchronization

When network connectivity resumes (e.g. iPhone awakens from sleep or Wi-Fi reconnects):
1. **Health Verification**: Calls `GET /api/v1/health` to verify host operational status and clock drift.
2. **Session Token Check**: Calls `GET /api/v1/status`. If token was revoked while offline, transitions to `FAILED` with `REVOKED_DEVICE`.
3. **Capabilities Refresh**: Re-fetches `GET /api/v1/capabilities`.
4. **WebSocket Resubscription**: Re-opens WebSocket connection to `/ws/v1/events?token=...`.
5. **Active Task Sync**: If a task was pending before disconnect, checks `GET /api/v1/agent/tasks/{id}` to restore completed response or error state.
