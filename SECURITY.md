# NOVA Security Architecture & Threat Model

Security in NOVA is a primary invariant, not an afterthought. Autonomous agents operating on local workstations must never be given unrestricted access simply because they are driven by AI.

---

## 1. Threat Model

NOVA addresses five primary threat categories:

| Threat Category | Attack Vector / Failure Mode | NOVA Defense Invariant |
|---|---|---|
| **Path Traversal & Host Escape** | Prompt injection or malformed tool call attempts to read or write files outside project (e.g. `C:\Windows`, `~/.ssh`). | **Workspace Confinement**: Robust path normalization with Windows case-folding blocks any target path outside `workspace_root`. |
| **Arbitrary Command Execution** | Model invokes shell commands (`run_command`) executing malware, destructive deletion (`rm -rf`), or privilege escalation. | **5-Tier Risk Gating**: Shell execution is classified as `CRITICAL` and strictly denied in Phase 01. Future phases mandate human approval. |
| **Secret Exfiltration & Leakage** | API keys or credentials printed to logs, console, or persisted into memory stores. | **Automated Secret Scrubbing**: `redact_sensitive_data()` strips keys and tokens before writing to JSONL audit or memory files. |
| **State Mutation Hallucination** | Agent claims a file was created or modified when the operation actually failed. | **Post-Action Epistemic Verification**: NOVA enforces empirical validation before declaring a task completed. |
| **Local Data Leakage** | Context, user preferences, or task history transmitted to third-party tracking services. | **Local-First Isolation**: All memory and audit logs are retained locally on the workstation under `.nova/`. |

---

## 2. Least Privilege Architecture

### Initial Read-Only Posture (Phase 01)
In Phase 01, NOVA's runtime exposes **only** safe, read-only tools:
- Allowed: `list_directory`, `search_directory`, `find_file`, `view_file`, `read_url_content`, `finish`.
- Restricted / Blocked: `create_file`, `edit_file`, `run_command`, `invoke_subagent`.

### 5-Tier Risk Classification
1. **`READ_ONLY`**: Zero state mutation, pure inspection.
2. **`LOW`**: Minimal non-destructive operations (web search).
3. **`MEDIUM`**: Reversible modifications within workspace boundaries. Requires interactive human confirmation in `STANDARD` mode.
4. **`HIGH`**: Irreversible state alterations or external communications.
5. **`CRITICAL`**: Shell execution (`run_command`), host-level configuration. Denied by default.

---

## 3. Human-in-the-Loop Approvals

When higher-risk tools are enabled in future phases:
- The `ApprovalHandler` interface provides structured inspection before execution:
  - Tool name
  - Evaluated risk tier
  - Exact argument dictionary
  - Reason approval is required
- Interactive CLI confirmation requires explicit human authorization (`[y/N]`).
- Any unapproved or timed-out request fails closed (`Decision.DENY`).

---

## 4. Secret & Credential Management

1. **No Hardcoded Secrets**: All API tokens and credentials must be supplied via environment variables or `.env`.
2. **Safe Representations**: Credentials in memory are encapsulated via `pydantic.SecretStr` to prevent accidental string casting.
3. **Audit Scrubbing**: The audit trail enforces automated regex scrubbing for Google API keys (`AIzaSy...`), Bearer tokens, and sensitive key names.

---

## 5. Future Sandboxing Roadmap

For subsequent phases introducing file mutations and terminal execution:
- Process isolation via containerization or Windows Sandbox.
- Restricted process tokens without administrative privileges.
- Network isolation for local script execution.
