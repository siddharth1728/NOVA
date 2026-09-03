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

### Controlled Mutation Posture (Phase 02)
In Phase 02, NOVA introduces safe, reversible filesystem operations:
- **Allowed with Approval**: `create_directory`, `create_file`, `edit_file`, `rename_file`, `move_file`, `copy_file` (classified as `MEDIUM` risk, requiring user confirmation in `STANDARD` mode).
- **Strictly Blocked**: Arbitrary shell execution (`run_command`), OS service alterations, and system configuration modifications remain denied by default.
- **Canonical Confinement**: `resolve_and_confine` enforces absolute containment within `workspace_root`, normalizing Windows drive letters and case insensitivity while rejecting directory traversal.
- **Stale-State Protection**: Edits verify SHA-256 pre-hashes against disk state. If external modifications occurred, `FILE_CHANGED_SINCE_PLAN` is raised to prevent silent overwrites.
- **Plan Drift Guard**: Executed steps must cryptographically match the approved plan hash. In-flight modifications raise `PlanDriftError`.
- **LIFO Rollback**: Multi-step transactions execute atomically with automated snapshot backups under `.nova/backups/`. Mid-plan failures automatically roll back completed operations in reverse order.

### 5-Tier Risk Classification
1. **`READ_ONLY`**: Zero state mutation, pure inspection.
2. **`LOW`**: Minimal non-destructive operations (web search).
3. **`MEDIUM`**: Reversible modifications within workspace boundaries. Requires interactive human confirmation in `STANDARD` mode.
4. **`HIGH`**: Irreversible state alterations or external communications.
5. **`CRITICAL`**: Shell execution (`run_command`), host-level configuration. Denied by default.

---

## 3. Human-in-the-Loop Approvals

- Interactive CLI confirmation requires explicit human authorization (`[y/N]`) before any mutation transaction begins.
- The approval prompt transparently details the goal, number of operations, target paths, and risk tier.
- Any unapproved or cancelled request fails closed, making zero filesystem modifications.

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
