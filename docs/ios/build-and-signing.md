# NOVA iOS Control Center: Build, Code Signing & Deployment

## 1. Overview

The NOVA iOS Control Center (`ios/NOVA`) is a native Swift 6 / SwiftUI application designed for iOS 17.0 and iOS 18.0+.
Because the development host environment for the NOVA Windows Host is Windows 11, the iOS client codebase is maintained cleanly decoupled from macOS-specific Xcode build artifacts.

To build, test, and deploy the iOS application to an iPhone or TestFlight, the `ios/` folder must be opened on macOS with Xcode.

---

## 2. Prerequisites (macOS Environment)

* **Operating System**: macOS Sonoma 14.5+ or macOS Sequoia 15.0+
* **Xcode**: Xcode 16.0+ (with Swift 6 compiler toolchain)
* **Apple Developer Program**: Enrolled account for physical device code signing and TestFlight distribution
* **CocoaPods / SPM**: Zero third-party package dependencies required (pure native Swift `Foundation`, `SwiftUI`, `Security`, `Combine`)

---

## 3. Local Development Build (Xcode Simulator or Connected iPhone)

1. Clone or sync the repository to your macOS workstation:
   ```bash
   git clone https://github.com/siddharth1728/NOVA.git
   cd NOVA/ios
   ```

2. Open the package in Xcode:
   ```bash
   xed .
   ```
   *Or open `NOVA.xcodeproj` / create a new iOS App target pointing to `NOVA/`.*

3. Set the active scheme to `NOVAiOS` and select an iOS Simulator (e.g., iPhone 16 Pro) or your connected physical iPhone.

4. Build and Run:
   * Press `Cmd + R` or click the Play button in Xcode.

---

## 4. Required Entitlements & Info.plist Permissions

To ensure smooth LAN discovery and communication between your iPhone and the Windows NOVA Host over Wi-Fi, the following keys must be present in the application's `Info.plist`:

### Local Network Usage Description
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>NOVA requires access to your local Wi-Fi network to connect securely to your Windows PC host agent.</string>
```

### Bonjour / Service Discovery (Optional / ZeroConf)
```xml
<key>NSBonjourServices</key>
<array>
    <string>_nova._tcp</string>
</array>
```

### App Transport Security (ATS) for Local Development HTTP
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```
*Note: In production LAN deployments, TLS/HTTPS with a self-signed or local PKI certificate is recommended.*

---

## 5. Device Pairing & First-Time Connection

1. On your Windows PC, launch the host service and generate a pairing PIN:
   ```powershell
   nova host start
   # In a second shell:
   nova host pair-code
   ```
2. On your iPhone, launch the **NOVA Control Center** app.
3. Tap **Settings** -> **Pair New Device**.
4. Enter your Windows PC's LAN IP address and port (e.g., `http://192.168.1.150:8000`).
5. Enter the 6-digit PIN displayed in the Windows terminal (e.g., `961 003`).
6. Tap **Pair This Device**. The device will be registered in `.nova/devices.json` and a JWT token will be saved securely to the iOS Keychain.

---

## 6. TestFlight & App Store Distribution

1. **Automatic Signing**: In Xcode, navigate to `Signing & Capabilities`, enable **Automatically manage signing**, and select your Apple Developer Team.
2. **Bundle Identifier**: Configure `com.yourdomain.nova.ios` (or team standard).
3. **Archive**: Select `Product` -> `Archive`.
4. **Distribute**: In the Xcode Organizer, select **Distribute App** -> **TestFlight & App Store**.
5. Once processed in App Store Connect, invite internal or external testers via TestFlight.
