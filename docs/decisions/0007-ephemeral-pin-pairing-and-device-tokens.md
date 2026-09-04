# ADR 0007: Ephemeral PIN Pairing & Device Session Tokens

## Status
Accepted (Phase 03)

## Context
Connecting a mobile client to a computer execution agent without authentication creates critical vulnerabilities, including unauthorized remote access, eavesdropping on screen captures, and remote query injection.
Hardcoded API keys or static credentials on mobile are fragile, difficult to rotate, and vulnerable to extraction.

## Decision
1. **6-Digit Ephemeral Pairing PIN**:
   To onboard a new mobile device, the user executes `nova host pair-code` in their Windows terminal.
   The host generates a cryptographically random 6-digit numeric PIN with a strict 300-second (5 minute) expiration window.
2. **One-Time Consumption**:
   Upon the first valid `/api/v1/pair` request matching the active PIN, the code is immediately purged from memory, preventing replay attacks.
3. **Signed JWT Device Session Tokens**:
   Upon pairing, the host records the client's unique device ID in `.nova/devices.json` and issues an HMAC-SHA256 signed JWT bearer token valid for 30 days.
4. **Host Revocation**:
   Workstation hosts can revoke access for any device at any time via `nova host revoke <device_id>` or `POST /api/v1/devices/{device_id}/revoke`. Future requests from revoked devices are immediately rejected with HTTP 403 `REVOKED_DEVICE`.

## Consequences
- **Positive**: Zero shared secrets transmitted over insecure channels; simple user onboarding flow mirroring Bluetooth/AirPlay pairing; instant workstation-side revocation capability.
- **Negative**: Requires physical access to the Windows host terminal to view the initial 6-digit pairing code.
