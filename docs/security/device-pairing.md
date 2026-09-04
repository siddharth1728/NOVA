# Device Pairing & Remote Security Model

## 1. Threat Analysis

Exposing workstation control over local or remote networks introduces several primary threat vectors:
1. **Unauthorized LAN Access**: Malicious nodes on the same Wi-Fi network attempting to control the agent.
2. **Replay Attacks**: Intercepted pairing PINs or session tokens re-used to establish sessions.
3. **Eavesdropping**: Snooping on desktop screen captures or agent reasoning logs.
4. **Remote Code Execution (RCE)**: Attempting to invoke arbitrary shell commands (`run_command`, PowerShell) over remote channels.

---

## 2. Defensive Controls

### 2.1 Ephemeral PIN Pairing
* Pairing codes are strictly 6-digit numeric values generated using Python's `secrets.randbelow`.
* Codes expire after 300 seconds (5 minutes).
* Codes are single-use: upon the first successful `/api/v1/pair` invocation, the code is immediately destroyed.

### 2.2 Device Trust Registry
* Authorized devices are stored persistently in `.nova/devices.json`.
* Every request must present a valid JWT signed by the host secret key.
* The host checks the device's lifecycle status on every request:
  * `ACTIVE`: Request permitted.
  * `REVOKED`: Request denied with HTTP 403 `REVOKED_DEVICE`.
  * Unknown / Unpaired: Request denied with HTTP 401 `UNAUTHENTICATED`.

### 2.3 Strict Remote Command Policy
* Under NOVA security policy, high-risk arbitrary command execution (`run_command`, PowerShell, `cmd.exe`) is **strictly prohibited over remote protocol**.
* Any remote query containing explicit shell execution attempts is immediately blocked with HTTP 403 `REMOTE_EXECUTION_DENIED`.
* File mutations remain strictly confined within `settings.workspace_root`.
