# NOVA Threat Model Specification

Detailed threat model for the NOVA agent operating layer.

---

## 1. Trust Boundaries

```
[ Untrusted External World ] (Web, user prompts, untrusted repositories)
           │
           │ Prompt / Input
           ▼
[ NOVA Agent Runtime ] (Strict epistemic rules, no code execution privilege)
           │
           │ Tool Request
           ▼
[ Security & Permission Engine ] ◄─── Human Approval Gate
           │
           │ Confinement Verified & Approved
           ▼
[ Antigravity Policy Layer ]
           │
           │ Native RPC Handshake
           ▼
[ Local Harness / OS Tools ] (Host filesystem confined to workspace_root)
```

---

## 2. Threat Scenarios & Mitigations

### 2.1 Workspace Escape via Symbolic Links or Path Traversal
- **Threat**: An agent or injected prompt targets paths like `../../Windows/System32` or `c:/users/other`.
- **Mitigation**: `check_workspace_containment()` resolves target paths to canonical absolute representations (`Path.resolve()`), handles Windows case-insensitivity (`os.path.normcase`), and verifies that the target path is strictly prefixed by `workspace_root`.

### 2.2 Shell Command Injection
- **Threat**: Injected instructions convince the model to invoke `run_command` with dangerous arguments (e.g. `rmdir /s /q`).
- **Mitigation**: `run_command` is classified as `CRITICAL` risk and strictly denied in Phase 01. In subsequent phases, any execution requires interactive console approval (`ApprovalHandler`).

### 2.3 Secret Leakage to Audit Logs
- **Threat**: API keys, user tokens, or authorization headers logged in telemetry files.
- **Mitigation**: `redact_sensitive_data()` scans dictionaries, lists, and string payloads using regex filters targeting Google API keys (`AIzaSy...`), Bearer tokens, and sensitive key names (`password`, `token`, `secret`, `credential`).
