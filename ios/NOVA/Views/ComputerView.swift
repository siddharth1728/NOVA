//
//  ComputerView.swift
//  NOVA iOS Control Center
//
//  Desktop screen capture inspection, virtual touchpad, keyboard, window management,
//  application discovery/launching, process inspection, and workstation security.
//

import SwiftUI

public enum ComputerControlTab: String, CaseIterable, Identifiable {
    case touchpad = "Touchpad"
    case keyboard = "Keyboard"
    case windows = "Windows"
    case apps = "Apps"
    case processes = "Processes"

    public var id: String { rawValue }

    public var icon: String {
        switch self {
        case .touchpad: return "hand.point.up.left.fill"
        case .keyboard: return "keyboard.fill"
        case .windows: return "macwindow.on.rectangle"
        case .apps: return "app.badge.fill"
        case .processes: return "gearshape.2.fill"
        }
    }
}

public struct ComputerView: View {
    @ObservedObject private var appModel = NovaAppModel.shared
    @State private var uiImage: UIImage?
    @State private var selectedTab: ComputerControlTab = .touchpad

    // Windows state
    @State private var windows: [WindowInfo] = []
    @State private var isLoadingWindows = false
    @State private var windowToClose: WindowInfo? = nil
    @State private var showCloseConfirmation = false

    // Apps state
    @State private var apps: [AppInfo] = []
    @State private var appSearchText = ""
    @State private var isLoadingApps = false

    // Processes state
    @State private var processes: [ProcessInfo] = []
    @State private var processSearchText = ""
    @State private var isLoadingProcesses = false
    @State private var processToStop: ProcessInfo? = nil
    @State private var showStopProcessConfirmation = false

    // Keyboard state
    @State private var typedText = ""

    // Status feedback
    @State private var actionFeedback: String? = nil
    @State private var showLockConfirmation = false
    @State private var isLocking = false

    public init() {}

    private func isCapabilityAvailable(_ name: String) -> Bool {
        guard let caps = appModel.capabilities?.capabilities else { return true }
        return caps.first(where: { $0.name == name })?.available ?? true
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    // Desktop Screen Canvas
                    screenCanvas

                    // Screen Metadata Details
                    if let meta = appModel.lastScreenshot {
                        metadataBar(meta)
                    }

                    if let feedback = actionFeedback {
                        feedbackBanner(feedback)
                    }

                    if let err = appModel.errorMessage {
                        errorBanner(err)
                    }

                    // Mode Selector Bar
                    tabSelector

                    // Active Control Panel
                    switch selectedTab {
                    case .touchpad:
                        touchpadPanel
                    case .keyboard:
                        keyboardPanel
                    case .windows:
                        windowsPanel
                    case .apps:
                        appsPanel
                    case .processes:
                        processesPanel
                    }

                    // Emergency Workstation Security
                    workstationFooter
                }
                .padding(.horizontal)
                .padding(.bottom, 24)
            }
            .navigationTitle("Computer Control")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await captureScreen() }
                    } label: {
                        if appModel.isCapturingScreen {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(appModel.isCapturingScreen)
                }
            }
            .task {
                if appModel.lastScreenshot == nil {
                    await captureScreen()
                } else if let b64 = appModel.lastScreenshot?.imageBase64, let data = Data(base64Encoded: b64) {
                    self.uiImage = UIImage(data: data)
                }
                await loadWindows()
            }
            .alert("Lock Windows Workstation?", isPresented: $showLockConfirmation) {
                Button("Cancel", role: .cancel) {}
                Button("Lock PC Now", role: .destructive) {
                    Task { await executeLock() }
                }
            } message: {
                Text("This will invoke Win32 LockWorkStation immediately, securing your Windows session.")
            }
            .alert("Close Window?", isPresented: $showCloseConfirmation, presenting: windowToClose) { win in
                Button("Cancel", role: .cancel) {}
                Button("Close Window", role: .destructive) {
                    Task { await closeWindow(win.hwnd) }
                }
            } message: { win in
                Text("Are you sure you want to close '\(win.title)' (HWND \(win.hwnd))? Any unsaved changes in this application may be lost.")
            }
            .alert("Terminate Process?", isPresented: $showStopProcessConfirmation, presenting: processToStop) { proc in
                Button("Cancel", role: .cancel) {}
                Button("Terminate Process", role: .destructive) {
                    Task { await terminateProcess(proc.pid) }
                }
            } message: { proc in
                Text("Are you sure you want to terminate '\(proc.name)' (PID \(proc.pid))?")
            }
        }
    }

    // MARK: - Screen Canvas

    private var screenCanvas: some View {
        ZStack {
            Color.black
                .frame(height: 200)
                .clipShape(RoundedRectangle(cornerRadius: 14))

            if let img = uiImage {
                Image(uiImage: img)
                    .resizable()
                    .scaledToFit()
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(3)
            } else if appModel.isCapturingScreen {
                VStack(spacing: 8) {
                    ProgressView()
                        .tint(.white)
                    Text("Capturing Desktop Frame...")
                        .font(.caption)
                        .foregroundStyle(.white)
                }
            } else {
                VStack(spacing: 8) {
                    Image(systemName: "display")
                        .font(.system(size: 36))
                        .foregroundStyle(.gray)
                    Text("No Screen Snapshot Captured")
                        .font(.caption)
                        .foregroundStyle(.gray)
                    Button("Capture Screen") {
                        Task { await captureScreen() }
                    }
                    .font(.caption.bold())
                    .buttonStyle(.borderedProminent)
                }
            }
        }
    }

    private func metadataBar(_ data: ScreenCaptureResponse) -> some View {
        HStack(spacing: 8) {
            Text("SCREEN PREVIEW")
                .font(.system(size: 9, weight: .black))
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.blue.opacity(0.15))
                .foregroundStyle(.blue)
                .clipShape(Capsule())

            Spacer()
            Label("\(data.width) × \(data.height)", systemImage: "aspectratio")
            Spacer()
            Label("\(data.fileSizeBytes / 1024) KB", systemImage: "doc")
            Spacer()
            Label(data.format.uppercased(), systemImage: "photo")
        }
        .font(.caption2)
        .foregroundStyle(.secondary)
        .padding(.horizontal, 4)
    }

    // MARK: - Tab Selector

    private var tabSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(ComputerControlTab.allCases) { tab in
                    Button {
                        selectedTab = tab
                        if tab == .windows { Task { await loadWindows() } }
                        if tab == .apps { Task { await loadApps() } }
                        if tab == .processes { Task { await loadProcesses() } }
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: tab.icon)
                            Text(tab.rawValue)
                        }
                        .font(.footnote.bold())
                        .padding(.vertical, 8)
                        .padding(.horizontal, 12)
                        .background(selectedTab == tab ? Color.blue : Color(.secondarySystemBackground))
                        .foregroundStyle(selectedTab == tab ? .white : .primary)
                        .clipShape(Capsule())
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }

    // MARK: - Touchpad Panel

    private var touchpadPanel: some View {
        VStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color(.secondarySystemBackground))
                    .frame(height: 180)
                    .overlay(
                        VStack {
                            Image(systemName: "hand.draw")
                                .font(.title2)
                                .foregroundStyle(.tertiary)
                            Text("Virtual Touchpad — Drag to Move, Tap to Click")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    )
                    .gesture(
                        DragGesture(minimumDistance: 4)
                            .onChanged { val in
                                let dx = Int(val.translation.width)
                                let dy = Int(val.translation.height)
                                Task {
                                    try? await NovaClient.shared.sendMouseMove(x: dx, y: dy)
                                }
                            }
                    )
                    .onTapGesture {
                        Task {
                            try? await NovaClient.shared.sendMouseClick(button: "left")
                            flashFeedback("Left Click")
                        }
                    }
                    .onLongPressGesture {
                        Task {
                            try? await NovaClient.shared.sendMouseClick(button: "right")
                            flashFeedback("Right Click")
                        }
                    }
            }

            // Click Buttons
            HStack(spacing: 12) {
                Button {
                    Task {
                        try? await NovaClient.shared.sendMouseClick(button: "left")
                        flashFeedback("Left Click")
                    }
                } label: {
                    Label("Left Click", systemImage: "hand.tap")
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.blue.opacity(0.15))
                        .foregroundStyle(.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                }
                .disabled(!isCapabilityAvailable("mouse_click"))

                Button {
                    Task {
                        try? await NovaClient.shared.sendMouseClick(button: "right")
                        flashFeedback("Right Click")
                    }
                } label: {
                    Label("Right Click", systemImage: "hand.tap.fill")
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.purple.opacity(0.15))
                        .foregroundStyle(.purple)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                }
                .disabled(!isCapabilityAvailable("mouse_click"))
            }

            // Scroll Buttons
            HStack(spacing: 12) {
                Button {
                    Task {
                        try? await NovaClient.shared.sendMouseScroll(clicks: 120)
                        flashFeedback("Scrolled Up")
                    }
                } label: {
                    Label("Scroll Up", systemImage: "arrow.up")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color(.tertiarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }

                Button {
                    Task {
                        try? await NovaClient.shared.sendMouseScroll(clicks: -120)
                        flashFeedback("Scrolled Down")
                    }
                } label: {
                    Label("Scroll Down", systemImage: "arrow.down")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color(.tertiarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Keyboard Panel

    private var keyboardPanel: some View {
        VStack(spacing: 12) {
            HStack {
                TextField("Type text to send to active window...", text: $typedText)
                    .textFieldStyle(.roundedBorder)
                    .autocapitalization(.none)

                Button("Send") {
                    let txt = typedText
                    typedText = ""
                    Task {
                        try? await NovaClient.shared.sendKeyboardType(text: txt)
                        flashFeedback("Sent: '\(txt)'")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(typedText.isEmpty || !isCapabilityAvailable("keyboard_type"))
            }

            // Quick Keys
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                quickKeyButton("Enter", key: "Enter")
                quickKeyButton("Esc", key: "Escape")
                quickKeyButton("Tab", key: "Tab")
                quickKeyButton("Backspace", key: "Backspace")
                quickKeyButton("Space", key: "Space")
                quickKeyButton("Win", key: "Win")
                quickKeyButton("Up", key: "Up")
                quickKeyButton("Down", key: "Down")
            }

            // Common Shortcuts
            HStack(spacing: 8) {
                shortcutButton("Ctrl+C", keys: ["ctrl", "c"])
                shortcutButton("Ctrl+V", keys: ["ctrl", "v"])
                shortcutButton("Ctrl+Z", keys: ["ctrl", "z"])
                shortcutButton("Alt+Tab", keys: ["alt", "tab"])
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private func quickKeyButton(_ label: String, key: String) -> some View {
        Button {
            Task {
                try? await NovaClient.shared.sendKeyPress(key: key)
                flashFeedback("Key: \(label)")
            }
        } label: {
            Text(label)
                .font(.caption.bold())
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func shortcutButton(_ label: String, keys: [String]) -> some View {
        Button {
            Task {
                try? await NovaClient.shared.sendKeyPress(key: keys.joined(separator: "+"))
                flashFeedback("Combo: \(label)")
            }
        } label: {
            Text(label)
                .font(.caption.bold())
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(Color.blue.opacity(0.1))
                .foregroundStyle(.blue)
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    // MARK: - Windows Panel

    private var windowsPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Open Windows (\(windows.count))")
                    .font(.subheadline.bold())
                Spacer()
                Button {
                    Task { await loadWindows() }
                } label: {
                    if isLoadingWindows {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }

            if windows.isEmpty && !isLoadingWindows {
                Text("No open application windows detected.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            } else {
                ForEach(windows) { win in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(win.title.isEmpty ? win.processName : win.title)
                                .font(.footnote.bold())
                                .lineLimit(1)
                            Text("\(win.processName) • PID \(win.processId) • HWND \(win.hwnd)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        Button("Focus") {
                            Task { await focusWindow(win.hwnd) }
                        }
                        .font(.caption.bold())
                        .buttonStyle(.bordered)

                        Button(role: .destructive) {
                            windowToClose = win
                            showCloseConfirmation = true
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.red)
                        }
                    }
                    .padding(.vertical, 4)
                    Divider()
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Apps Panel

    private var appsPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                TextField("Search installed apps...", text: $appSearchText)
                    .textFieldStyle(.roundedBorder)
                    .onChange(of: appSearchText) { _ in
                        Task { await loadApps() }
                    }

                Button {
                    Task { await loadApps() }
                } label: {
                    if isLoadingApps {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "magnifyingglass")
                    }
                }
            }

            if apps.isEmpty && !isLoadingApps {
                Text("No matching applications found.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            } else {
                ForEach(apps.prefix(12)) { app in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(app.name)
                                .font(.footnote.bold())
                            if let pub = app.publisher {
                                Text(pub)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Spacer()

                        Button("Launch") {
                            Task { await launchApp(app.executablePath) }
                        }
                        .font(.caption.bold())
                        .buttonStyle(.borderedProminent)
                        .disabled(!isCapabilityAvailable("app_launch"))
                    }
                    .padding(.vertical, 4)
                    Divider()
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Processes Panel

    private var processesPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                TextField("Filter processes...", text: $processSearchText)
                    .textFieldStyle(.roundedBorder)
                    .onChange(of: processSearchText) { _ in
                        Task { await loadProcesses() }
                    }

                Button {
                    Task { await loadProcesses() }
                } label: {
                    if isLoadingProcesses {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }

            if processes.isEmpty && !isLoadingProcesses {
                Text("No processes matching filter.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            } else {
                ForEach(processes.prefix(15)) { proc in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            HStack {
                                Text(proc.name)
                                    .font(.footnote.bold())
                                if proc.isProtected {
                                    Text("PROTECTED")
                                        .font(.system(size: 9, weight: .black))
                                        .foregroundStyle(.orange)
                                        .padding(.horizontal, 4)
                                        .padding(.vertical, 1)
                                        .background(Color.orange.opacity(0.15))
                                        .clipShape(Capsule())
                                }
                            }
                            Text("PID \(proc.pid) • CPU \(String(format: "%.1f", proc.cpuPercent))% • \(String(format: "%.0f", proc.memoryMb)) MB")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        if !proc.isProtected {
                            Button("Stop") {
                                processToStop = proc
                                showStopProcessConfirmation = true
                            }
                            .font(.caption.bold())
                            .buttonStyle(.bordered)
                            .foregroundStyle(.red)
                        }
                    }
                    .padding(.vertical, 4)
                    Divider()
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Workstation Footer

    private var workstationFooter: some View {
        Button {
            showLockConfirmation = true
        } label: {
            Label("Emergency Lock Workstation", systemImage: "lock.shield.fill")
                .font(.subheadline.bold())
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.red.opacity(0.15))
                .foregroundStyle(.red)
                .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .disabled(isLocking)
    }

    // MARK: - Helpers & API Calls

    private func feedbackBanner(_ msg: String) -> some View {
        HStack {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
            Text(msg)
                .font(.caption.bold())
                .foregroundStyle(.green)
            Spacer()
        }
        .padding(10)
        .background(Color.green.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func errorBanner(_ msg: String) -> some View {
        HStack {
            Image(systemName: "exclamationmark.circle.fill")
                .foregroundStyle(.red)
            Text(msg)
                .font(.caption)
                .foregroundStyle(.red)
            Spacer()
        }
        .padding()
        .background(Color.red.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func flashFeedback(_ msg: String) {
        withAnimation {
            actionFeedback = msg
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation {
                if actionFeedback == msg {
                    actionFeedback = nil
                }
            }
        }
    }

    private func captureScreen() async {
        await appModel.captureDesktopSnapshot(maxWidth: 1280)
        if let b64 = appModel.lastScreenshot?.imageBase64, let data = Data(base64Encoded: b64) {
            self.uiImage = UIImage(data: data)
        }
    }

    private func loadWindows() async {
        isLoadingWindows = true
        if let res = try? await NovaClient.shared.listWindows() {
            windows = res
        }
        isLoadingWindows = false
    }

    private func focusWindow(_ hwnd: Int) async {
        do {
            try await NovaClient.shared.focusWindow(hwnd: hwnd)
            flashFeedback("Focused window (HWND \(hwnd))")
            await captureScreen()
        } catch {
            appModel.errorMessage = error.localizedDescription
        }
    }

    private func closeWindow(_ hwnd: Int) async {
        do {
            try await NovaClient.shared.closeWindow(hwnd: hwnd)
            flashFeedback("Closed window (HWND \(hwnd))")
            await loadWindows()
            await captureScreen()
        } catch {
            appModel.errorMessage = error.localizedDescription
        }
    }

    private func loadApps() async {
        isLoadingApps = true
        let q = appSearchText.isEmpty ? nil : appSearchText
        if let res = try? await NovaClient.shared.listApps(search: q) {
            apps = res
        }
        isLoadingApps = false
    }

    private func launchApp(_ path: String) async {
        do {
            let res = try await NovaClient.shared.launchApp(appNameOrPath: path)
            if res.success {
                flashFeedback("Launched application (PID \(res.pid ?? 0))")
                await loadWindows()
                await captureScreen()
            } else {
                appModel.errorMessage = res.message ?? "Launch failed"
            }
        } catch {
            appModel.errorMessage = error.localizedDescription
        }
    }

    private func loadProcesses() async {
        isLoadingProcesses = true
        let q = processSearchText.isEmpty ? nil : processSearchText
        if let res = try? await NovaClient.shared.listProcesses(search: q, top: 25) {
            processes = res
        }
        isLoadingProcesses = false
    }

    private func terminateProcess(_ pid: Int) async {
        do {
            let res = try await NovaClient.shared.stopProcess(pid: pid)
            if res.success {
                flashFeedback("Terminated PID \(pid)")
                await loadProcesses()
            } else {
                appModel.errorMessage = res.message ?? "Failed to stop process"
            }
        } catch {
            appModel.errorMessage = error.localizedDescription
        }
    }

    private func executeLock() async {
        isLocking = true
        await appModel.emergencyLockWorkstation()
        isLocking = false
    }
}

