# NOVA Mobile Networking & Transport Security

## 1. Network Topology Options

To allow an iPhone to communicate with the Windows NOVA Host, three networking topologies are supported:

### Option A: Local Wi-Fi (Same Subnet)
* Both iPhone and Windows PC are connected to the same home/office Wi-Fi router.
* Host listens on `0.0.0.0:8000`.
* iPhone connects to `http://<PC_LOCAL_IP>:8000` (e.g. `http://192.168.1.50:8000`).

### Option B: Tailscale / WireGuard (Recommended for Secure Remote Access)
* Install [Tailscale](https://tailscale.com) on both Windows PC and iPhone.
* Both devices join your private Tailnet.
* iPhone connects to the PC's 100.x.y.z Tailscale IP (e.g. `http://100.85.12.34:8000`).
* **Security Benefits**: End-to-end encrypted WireGuard tunnel, works across cellular data and external Wi-Fi networks without opening router ports.

### Option C: Reverse Proxy with TLS (Production LAN)
* Run Caddy or Nginx on Windows in front of NOVA Host (e.g. `caddy reverse-proxy --from https://pc.local --to :8000`).
* Provides valid TLS certificate for HTTPS and WSS connections.

---

## 2. Windows Defender Firewall Configuration

When running NOVA Host on Windows, inbound TCP traffic on port 8000 must be permitted across private networks:

### Allow Port via PowerShell (Run as Administrator if prompted):
```powershell
New-NetFirewallRule -DisplayName "NOVA Windows Host" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```

To verify the rule:
```powershell
Get-NetFirewallRule -DisplayName "NOVA Windows Host"
```

---

## 3. iOS Local Network Permission

On iOS 14+, apps communicating with LAN devices require explicit user permission.
NOVA configures this via `Info.plist`:
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>NOVA requires access to your local Wi-Fi network to connect securely to your Windows PC host agent.</string>
```
When first launching the app, tap **Allow** when prompted: *"NOVA would like to find and connect to devices on your local network."*
