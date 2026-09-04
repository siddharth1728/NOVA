//
//  SettingsView.swift
//  NOVA iOS Control Center
//
//  Host endpoint configuration, device identity, capability discovery, and unpairing controls.
//

import SwiftUI

public struct SettingsView: View {
    @ObservedObject private var appModel = NovaAppModel.shared
    @State private var showPairingSheet = false
    @State private var hostUrl = KeychainStore.shared.hostBaseUrl
    @State private var isEditingHostUrl = false

    public init() {}

    public var body: some View {
        NavigationStack {
            Form {
                // Connection State Section
                Section("Connection Status") {
                    HStack {
                        Text("Lifecycle State")
                        Spacer()
                        Text(appModel.connectionState.rawValue)
                            .font(.caption.bold())
                            .foregroundStyle(connectionColor)
                    }

                    if let latency = appModel.latencyMs {
                        HStack {
                            Text("Roundtrip Latency")
                            Spacer()
                            Text("\(latency) ms")
                                .font(.system(.caption, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }
                    }

                    if appModel.isPaired {
                        Button("Reconnect Now") {
                            Task { await appModel.establishConnection() }
                        }
                    }
                }

                // Device Trust & Pairing Section
                Section("Device Trust & Identity") {
                    HStack {
                        Text("Device ID")
                        Spacer()
                        Text(KeychainStore.shared.deviceId.prefix(12) + "...")
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Trust Status")
                        Spacer()
                        Text(appModel.isPaired ? "Paired & Authorized" : "Unpaired")
                            .font(.caption.bold())
                            .foregroundStyle(appModel.isPaired ? .green : .red)
                    }

                    Button(appModel.isPaired ? "Re-Pair Device" : "Pair New Device") {
                        showPairingSheet = true
                    }
                }

                // Workstation Endpoint Section
                Section("Host Workstation") {
                    if isEditingHostUrl {
                        HStack {
                            TextField("http://192.168.1.100:8000", text: $hostUrl)
                                .autocorrectionDisabled()
                                .textInputAutocapitalization(.never)
                                .keyboardType(.URL)
                            Button("Save") {
                                KeychainStore.shared.hostBaseUrl = hostUrl
                                isEditingHostUrl = false
                                Task { await appModel.establishConnection() }
                            }
                            .font(.caption.bold())
                        }
                    } else {
                        HStack {
                            Text("Host URL")
                            Spacer()
                            Text(KeychainStore.shared.hostBaseUrl)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Button("Edit Host Endpoint") {
                            isEditingHostUrl = true
                        }
                    }
                }

                // Host Capabilities Section
                Section("Discovered Capabilities") {
                    if let caps = appModel.capabilities {
                        ForEach(caps.capabilities) { cap in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(cap.name)
                                        .font(.subheadline.bold())
                                    Text(cap.description)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Text(cap.riskLevel)
                                    .font(.caption2.bold())
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(cap.available ? Color.blue.opacity(0.1) : Color.red.opacity(0.1))
                                    .foregroundStyle(cap.available ? Color.blue : Color.red)
                                    .clipShape(Capsule())
                            }
                        }
                    } else {
                        Text("Capabilities will be discovered upon connection.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                // About NOVA
                Section("About NOVA") {
                    HStack {
                        Text("Application")
                        Spacer()
                        Text("NOVA for iOS")
                            .foregroundStyle(.secondary)
                    }
                    HStack {
                        Text("Client Version")
                        Spacer()
                        Text("0.4.0")
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    HStack {
                        Text("Protocol Version")
                        Spacer()
                        Text(PROTOCOL_VERSION)
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    HStack {
                        Text("Host Server Version")
                        Spacer()
                        Text(appModel.hostHealth?.serverVersion ?? "Offline")
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    if let osVer = appModel.systemStatus?.system.osVersion {
                        HStack {
                            Text("Workstation OS")
                            Spacer()
                            Text(osVer)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                // Security & Danger Zone
                Section("Security Actions") {
                    Button("Unpair & Clear Credentials", role: .destructive) {
                        appModel.unpairDevice()
                    }
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showPairingSheet) {
                PairingView(isPresented: $showPairingSheet)
            }
        }
    }

    private var connectionColor: Color {
        switch appModel.connectionState {
        case .connected: return .green
        case .connecting, .authenticating, .reconnecting: return .blue
        case .degraded: return .orange
        case .disconnected, .failed: return .red
        }
    }
}
