# NOVA for iOS — Native Client Deployment & Verification Guide

NOVA for iOS is a native SwiftUI client designed for iOS 17.0+ that connects securely to the NOVA Windows Host over local Wi-Fi, Tailscale, or private network transport.

This document details the build prerequisites, project generation, code signing, physical iPhone installation, pairing workflow, and architectural guarantees.

---

## 1. Product Architecture

The native iOS application follows an observable, single-source-of-truth architecture:

* **State Store (`NovaAppModel` / `NOVAAppModel`)**:
  * Single authoritative `@MainActor` observable object managing lifecycle state (`disconnected`, `connecting`, `authenticating`, `connected`, `degraded`, `reconnecting`, `failed`), real-time telemetry, agent execution status, and desktop previews.
* **Secure Storage (`KeychainStore`)**:
  * Utilizes Apple's native Security framework (`kSecClassGenericPassword`) to store device UUIDs, JWT session tokens, and host endpoint configuration. Secrets are never saved in `UserDefaults`, unencrypted plist files, or app caches.
* **Network & API (`NovaClient`)**:
  * REST client communicating with Windows Host (`/api/v1/...`) with deterministic error taxonomy and automatic idempotency key generation (`UUID().uuidString`).
* **Real-Time Streaming (`ConnectionManager`)**:
  * Native `URLSessionWebSocketTask` client providing event streaming for telemetry, agent plan progress, step updates, and heartbeat/reconnect loops.
* **Branding & Assets**:
  * Full 1024×1024 native App Icon asset (`AppIcon.appiconset`) featuring the glowing cyan/violet NOVA star monogram on deep obsidian slate.

---

## 2. Build Prerequisites

To compile and install the native iOS binary onto a physical iPhone, the following environment is required:

* **Hardware**: Mac computer (Apple Silicon M1/M2/M3/M4 or Intel) running macOS Sonoma 14.5+ or macOS Sequoia 15.0+
* **Development Tooling**: Xcode 15.4 or Xcode 16.0+ (with iOS 17.0+ SDK)
* **Project Generator**: [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)
* **Apple Account**: Free Apple ID or Apple Developer Program membership
* **Device**: iPhone running iOS 17.0 or iOS 18.0+

---

## 3. Step-by-Step Build & Installation Guide

### Step 3.1: Clone or Copy Repository to Mac
Transfer or clone the repository to your Mac:
```bash
git clone https://github.com/siddharth1728/NOVA.git
cd NOVA/ios
```

### Step 3.2: Generate Xcode Project with XcodeGen
The `ios/` folder contains a declarative `project.yml` specification. Generate the `.xcodeproj` file by running:
```bash
xcodegen generate
```
This generates `NOVA.xcodeproj` configured with:
* Deployment Target: iOS 17.0
* Bundle Identifier: `com.antigravity.nova.ios`
* App Icon set configured to `AppIcon`
* Local Network Usage description embedded in `Info.plist`

### Step 3.3: Open Project in Xcode
Open the generated project:
```bash
open NOVA.xcodeproj
```
*(Alternatively, you can open `Package.swift` directly in Xcode as a Swift Package).*

### Step 3.4: Configure Signing & Team
1. In the Xcode Project Navigator, select the root **NOVA** project.
2. Select the **NOVA** target.
3. Switch to the **Signing & Capabilities** tab.
4. Check **Automatically manage signing**.
5. Select your **Team** from the dropdown (Personal Team works for free developer accounts).
6. If the Bundle Identifier `com.antigravity.nova.ios` is not unique to your Apple ID, append your initials (e.g., `com.yourname.nova.ios`).

### Step 3.5: Enable Developer Mode on iPhone
On your physical iPhone running iOS 17 or iOS 18:
1. Open **Settings**.
2. Navigate to **Privacy & Security** → scroll to the bottom.
3. Tap **Developer Mode** and toggle it **ON**.
4. Restart your iPhone when prompted.
5. After reboot, unlock your device and tap **Turn On**, then enter your passcode.

### Step 3.6: Connect Device & Deploy
1. Connect your iPhone to your Mac using a USB-C or Lightning cable.
2. If prompted on the iPhone, tap **Trust This Computer** and enter your passcode.
3. In the top toolbar of Xcode, select your physical iPhone as the active run destination.
4. Press **Cmd + R** (or click the **Run** ▶ button).
5. Xcode compiles the Swift source, packages the IPA, signs the binary, and installs NOVA directly onto your iPhone.

### Step 3.7: Trust Developer Profile (First Time Only)
When launching the app for the first time on device, iOS may display an "Untrusted Developer" alert:
1. Open **Settings** on your iPhone.
2. Navigate to **General** → **VPN & Device Management**.
3. Under **Developer App**, tap your Apple ID.
4. Tap **Trust "[Your Apple ID]"** and confirm **Trust**.
5. Return to the Home Screen and tap **NOVA**.

---

## 4. Workstation Pairing & Connection Workflow

### Step 4.1: Start NOVA Windows Host
On your Windows workstation:
```powershell
cd C:\KaryaSetu
.venv\Scripts\nova host start --host 0.0.0.0 --port 8000
```
Ensure your Windows Firewall allows inbound connections on port 8000 for your private Wi-Fi network.

### Step 4.2: Generate Ephemeral Pairing PIN
On the Windows PC, generate a temporary 6-digit pairing code:
```powershell
.venv\Scripts\nova host pair-code
```
Output:
```
Ephemeral Pairing PIN: 582194 (Valid for 5 minutes)
```

### Step 4.3: Pair from iPhone
1. Open the **NOVA** app on your iPhone.
2. On initial launch, NOVA presents the **Link Windows PC** sheet:
   * **Host Address**: Enter `http://<YOUR_PC_LAN_IP>:8000` (e.g. `http://192.168.1.100:8000` or Tailscale IP `http://100.x.y.z:8000`).
   * **Pairing Code**: Enter the 6-digit PIN generated above.
3. Tap **Pair This Device**.
4. The app exchanges the PIN for a cryptographically signed JWT bearer token, saves it into the iOS Keychain, and transitions into `CONNECTED` state.

---

## 5. Feature Verification Checklist

Once connected, verify each native surface:

* **Home Dashboard**:
  * Displays PC hostname (e.g., `WIN-DN39UMND4AV`), OS version, roundtrip latency in milliseconds.
  * Shows live gauges for CPU %, RAM (used/total GB), Disk %, and system uptime.
  * Agent status badge (`IDLE`, `PLANNING`, `EXECUTING`).
* **Computer Control**:
  * **Screen Preview**: Renders high-resolution desktop snapshot labeled `SCREEN PREVIEW` with dimensions and payload size. Tap refresh to update frame.
  * **Virtual Touchpad**: Pan on the touchpad surface to move the mouse cursor. Tap for Left Click, long-press for Right Click.
  * **Virtual Keyboard**: Send text input or special keys (`Enter`, `Esc`, `Tab`, `Backspace`, shortcuts) directly to the focused Windows window.
  * **Windows Drawer**: View list of all active top-level Windows applications. Tap to Focus, Resize, or Close (with confirmation prompt).
  * **Applications Drawer**: Discover installed Windows applications. Search and launch apps with a single tap.
  * **Process Inspection**: View top running processes sorted by CPU and memory. Terminate non-critical processes with approval confirmation.
  * **Workstation Security**: Tap "Lock PC" to invoke `LockWorkStation` immediately.
* **Agent Runtime**:
  * Submit natural language commands (e.g. *"Inspect git branch status"*).
  * View execution step progression and tool invocation count.
  * Tap **STOP TASK** to send a direct cancellation signal to the host task controller.
* **Settings**:
  * View connection state, roundtrip latency, discovered capabilities matrix with risk classifications, and unpair device button.
  * "About NOVA" section displays client version (`0.4.0`), protocol version (`1.0.0`), host version, and host OS.

---

## 6. Network & Transport Security

* **Local Wi-Fi Access**:
  * `Info.plist` includes `NSLocalNetworkUsageDescription` allowing direct discovery and communication on local subnets.
* **Cellular / Remote Access**:
  * For control outside your home/office Wi-Fi, install [Tailscale](https://tailscale.com/) on both Windows PC and iPhone. Enter the PC's Tailscale IPv4 address (`100.x.y.z:8000`) in NOVA settings for encrypted WireGuard mesh communication without port forwarding.
* **Zero Client Authority**:
  * The iOS client does not make security decisions. High-risk operations (closing windows, stopping processes, system commands) are validated and gated authoritatively by the Windows host control layer and security policies.
