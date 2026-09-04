//
//  SettingsView.swift
//  NOVA iOS Control Center
//
//  Host endpoint configuration, device identity, capability discovery, and unpairing controls.
//

import SwiftUI

public struct SettingsView: View {
    @State private var showPairingSheet = false
    @State private var hostUrl = KeychainStore.shared.hostBaseUrl
    @State private var deviceId = KeychainStore.shared.deviceId
    @State private var isPaired = KeychainStore.shared.isPaired
    @State private var capabilities: CapabilitiesMatrix?
    @State private var isLoadingCapabilities = false

    public init() {}

    public var body: some View {
        NavigationStack {
            Form {
                // Device Trust & Pairing Section
                Section("Device Trust & Identity") {
                    HStack {
                        Text("Device ID")
                        Spacer()
                        Text(deviceId.prefix(12) + "...")
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Status")
                        Spacer()
                        Text(isPaired ? "Paired & Authorized" : "Unpaired")
                            .font(.caption.bold())
                            .foregroundStyle(isPaired ? .green : .red)
                    }

                    Button(isPaired ? "Re-Pair Device" : "Pair New Device") {
                        showPairingSheet = true
                    }
                }

                // Workstation Endpoint Section
                Section("Host Workstation") {
                    HStack {
                        Text("Host URL")
                        Spacer()
                        Text(hostUrl)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                // Host Capabilities Section
                Section("Host Capabilities Matrix") {
                    if let caps = capabilities {
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
                    } else if isLoadingCapabilities {
                        ProgressView("Discovering Capabilities...")
                    } else {
                        Button("Inspect Host Capabilities") {
                            Task { await loadCapabilities() }
                        }
                    }
                }

                // Security & Danger Zone
                Section("Security Actions") {
                    Button("Unpair & Clear Credentials", role: .destructive) {
                        KeychainStore.shared.clearAll()
                        isPaired = false
                    }
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showPairingSheet) {
                PairingView(isPresented: $showPairingSheet) {
                    isPaired = KeychainStore.shared.isPaired
                    Task { await loadCapabilities() }
                }
            }
            .task {
                if isPaired {
                    await loadCapabilities()
                }
            }
        }
    }

    private func loadCapabilities() async {
        isLoadingCapabilities = true
        do {
            let res = try await NovaClient.shared.fetchCapabilities()
            self.capabilities = res
        } catch {
            print("Failed to load capabilities: \(error)")
        }
        isLoadingCapabilities = false
    }
}
