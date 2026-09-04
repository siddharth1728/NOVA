# NOVA iOS Control Center: Installation & Deployment Guide

## 1. Verified Physical iPhone Status

> **Current Verification Status**: **NOT YET VERIFIED ON PHYSICAL DEVICE**  
> **Host Environment**: Windows 11 (NT 10.0.26200.0) without local Xcode / macOS.  
> **Source State**: Swift 6 / SwiftUI source code authored, verified for protocol parity and automated CI build via GitHub Actions (`macos-14` runner).

Physical iPhone deployment requires a macOS environment with Xcode 16.0+ to compile the Swift package into an ARM64 iOS application binary signed with an Apple Developer certificate.

---

## 2. Installation Paths

### A. Development Build (Direct USB / Wi-Fi Install)
**Requirements**: Mac computer with macOS Sonoma/Sequoia, Xcode 16+, Free or Paid Apple ID.

1. **Clone repository to macOS**:
   ```bash
   git clone https://github.com/siddharth1728/NOVA.git
   cd NOVA/ios
   ```
2. **Generate Xcode Project or Open in Xcode**:
   - **Option 1 (SPM)**: Open Xcode, choose `File` -> `Open...`, and select `NOVA/ios`.
   - **Option 2 (XcodeGen)**: If `xcodegen` is installed (`brew install xcodegen`), run:
     ```bash
     xcodegen generate
     open NOVA.xcodeproj
     ```
3. **Connect physical iPhone**:
   - Connect your iPhone to your Mac via USB-C or Lightning cable.
   - Unlock your iPhone and tap **Trust This Computer**.
4. **Configure Code Signing**:
   - In Xcode project settings under **Signing & Capabilities**, check **Automatically manage signing**.
   - Select your personal Apple ID team.
5. **Install and Run**:
   - Select your connected iPhone in the device destination menu.
   - Click **Run** (`Cmd + R`).
   - On your iPhone: Go to **Settings** -> **General** -> **VPN & Device Management** -> Trust your developer profile.
   - Open the **NOVA** app.

---

### B. TestFlight Distribution (Internal & External Beta)
**Requirements**: Paid Apple Developer Program membership ($99/year).

1. In Xcode: Set scheme to **Any iOS Device (arm64)**.
2. Select **Product** -> **Archive**.
3. Once the archive completes in the Organizer window, click **Distribute App**.
4. Select **TestFlight & App Store** -> **Upload**.
5. Log into [App Store Connect](https://appstoreconnect.apple.com):
   - Navigate to your app -> **TestFlight** tab.
   - Add your email or team members to the Internal Testing group.
6. On your iPhone: Install the **TestFlight** app from the App Store and accept the invite to install NOVA.

---

### C. App Store Release
**Requirements**: Paid Apple Developer Program membership, app privacy manifest compliance.

1. Complete App Store listing metadata, screenshots, and privacy questionnaire in App Store Connect.
2. Select the approved TestFlight build.
3. Submit for App Review.
