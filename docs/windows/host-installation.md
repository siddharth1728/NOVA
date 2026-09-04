# NOVA Windows Host: Installation & Service Configuration

## 1. Prerequisites

* Windows 10/11 (64-bit)
* Python `>= 3.10`
* Virtual environment (`.venv`) initialized and dependencies installed:
  ```powershell
  uv venv .venv
  uv pip install -e ".[dev]"
  ```

---

## 2. Interactive Host Startup

To run NOVA Host interactively in PowerShell:

```powershell
# Binds to all local interfaces (Wi-Fi, Ethernet, Tailscale) on port 8000
.venv\Scripts\nova host start --host 0.0.0.0 --port 8000
```

The host displays:
- Active LAN endpoints (e.g. `http://192.168.1.50:8000`)
- WebSocket endpoint (`ws://0.0.0.0:8000/ws/v1/events`)
- Device registry file location (`.nova/devices.json`)

To generate an iPhone pairing code:
```powershell
.venv\Scripts\nova host pair-code
```

---

## 3. Persistent Background Service (Scheduled Task on Logon)

To have NOVA Host automatically launch in the background whenever you log into Windows:

### Register via PowerShell:
```powershell
$Action = New-ScheduledTaskAction -Execute "C:\KaryaSetu\.venv\Scripts\python.exe" -Argument "-m nova.main host start --host 0.0.0.0 --port 8000" -WorkingDirectory "C:\KaryaSetu"
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "NOVA_Host_Service" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs NOVA Windows Host on user logon"
```

### Check Service Status:
```powershell
Get-ScheduledTask -TaskName "NOVA_Host_Service"
```

### Stop / Unregister Task:
```powershell
Unregister-ScheduledTask -TaskName "NOVA_Host_Service" -Confirm:$false
```
