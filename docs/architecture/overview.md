# NOVA Architectural Overview

This document complements `ARCHITECTURE.md` with operational state diagrams and data flows.

---

## 1. Request Lifecycle & Verification Sequence

```
User Query
   │
   ▼
[NovaRuntime.query]
   │
   ├─► [Lifecycle: INITIALIZING -> READY -> PLANNING]
   │
   ├─► [Validate Config & Credentials]
   │
   ├─► [Synthesize Antigravity LocalAgentConfig & Policies]
   │
   ├─► [Lifecycle: EXECUTING]
   │       │
   │       ├─► [Agent.chat()] ──► [LocalHarness via WebSocket]
   │       │                            │
   │       │                            ├─► [PreToolCallDecideHook / Policies]
   │       │                            │       │
   │       │                            │       └─► Policy: allow / ask / deny
   │       │                            │
   │       │                            ├─► [Tool Execution (read-only)]
   │       │                            │
   │       │                            └─► [PostToolCallHook]
   │       │                                    │
   │       │                                    └─► [AuditTrail.log_tool_invocation]
   │       │
   │       └─► Stream Token Chunks
   │
   ├─► [Lifecycle: VERIFYING]
   │       │
   │       └─► [verify_outcome()] (Empirical check: are claims backed by tool results?)
   │
   ├─► [LocalFileMemoryStore.record_execution()]
   │
   └─► [Lifecycle: IDLE] ──► Return Verified Response
```

---

## 2. Risk Hierarchy & Policy Gate

```
Tool Risk Tier        Policy Default (Strict)        Policy (Standard)
───────────────────────────────────────────────────────────────────────────
READ_ONLY             ALLOW                          ALLOW
LOW                   DENY                           ALLOW
MEDIUM                DENY                           ASK (Approval Required)
HIGH                  DENY                           DENY
CRITICAL              DENY                           DENY (run_command)
```
