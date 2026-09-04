# NOVA Device Pairing & Trust Establishment

## 1. Overview

NOVA uses an ephemeral 6-digit numeric PIN pairing protocol. This prevents unauthorized nodes on the local network from commanding the agent or observing desktop screens.

```
[Windows Host PC]                                 [iPhone Client]
       │                                                 │
       │ 1. `nova host pair-code`                        │
       │    Generates 6-digit PIN (300s TTL)             │
       │                                                 │
       │ 2. User enters PIN into iPhone app              │
       │ ──────────────────────────────────────────────> │
       │                                                 │
       │ 3. POST /api/v1/pair (PIN + device_id)          │
       │ <────────────────────────────────────────────── │
       │                                                 │
       │ 4. Host verifies PIN, records device, issues    │
       │    HMAC-SHA256 JWT token                        │
       │ ──────────────────────────────────────────────> │
       │                                                 │
       │ 5. Subsequent requests carry Bearer token       │
```

---

## 2. Step-by-Step Pairing Flow

1. **Start the Host Service on Windows**:
   ```powershell
   nova host start --host 0.0.0.0 --port 8000
   ```
2. **Generate a Pairing Code**:
   In a separate terminal on the Windows host, execute:
   ```powershell
   nova host pair-code
   ```
   *Output:*
   ```text
   +---------------------------- Device Pairing Code ----------------------------+
   |                                                                             |
   |         961 003                                                             |
   |                                                                             |
   | Expires at: 11:40:26 UTC                                                    |
   | Enter this code in the NOVA iOS app to link this device.                    |
   +-----------------------------------------------------------------------------+
   ```
3. **Connect and Authorize in the iOS App**:
   - Open NOVA on your iPhone.
   - Tap **Settings** -> **Pair New Device**.
   - Enter your Windows host endpoint (e.g. `http://192.168.1.50:8000`).
   - Enter the 6-digit code `961003`.
   - Tap **Pair This Device**.
4. **Token Issuance & Persistence**:
   - The Windows host marks the device as `ACTIVE` in `.nova/devices.json`.
   - A signed JWT token is returned and stored securely in the iOS Keychain (`kSecClassGenericPassword`).
   - The temporary PIN is destroyed immediately to prevent replay attacks.

---

## 3. Revocation & Disconnection

### From Windows Terminal:
To revoke an iPhone's access:
```powershell
nova host devices
nova host revoke <device_id>
```
Once revoked, any future request from that device receives HTTP 403 `REVOKED_DEVICE`.

### From iPhone App:
To unpair:
- Tap **Settings** -> **Unpair & Clear Credentials**.
- The JWT token and device ID are wiped from Keychain and the connection is closed.
