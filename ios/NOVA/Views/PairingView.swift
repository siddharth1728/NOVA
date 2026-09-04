//
//  PairingView.swift
//  NOVA iOS Control Center
//
//  Host endpoint discovery and 6-digit PIN code device onboarding sheet.
//

import SwiftUI

public struct PairingView: View {
    @ObservedObject private var appModel = NovaAppModel.shared
    @Binding public var isPresented: Bool
    @State private var hostUrl: String = KeychainStore.shared.hostBaseUrl
    @State private var pairingCode: String = ""
    @State private var isPairing: Bool = false
    public var onPaired: (() -> Void)?

    public init(isPresented: Binding<Bool>, onPaired: (() -> Void)? = nil) {
        self._isPresented = isPresented
        self.onPaired = onPaired
    }

    public var body: some View {
        NavigationStack {
            Form {
                Section("Workstation Host Address") {
                    TextField("http://192.168.1.100:8000", text: $hostUrl)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                    Text("The local IP and port where your Windows PC is running 'nova host start' (e.g., http://192.168.1.50:8000 or Tailscale IP).")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("6-Digit Pairing Code") {
                    TextField("000000", text: $pairingCode)
                        .keyboardType(.numberPad)
                        .font(.system(.title2, design: .monospaced))
                        .multilineTextAlignment(.center)
                        .onChange(of: pairingCode) { _, newValue in
                            if newValue.count > 6 {
                                pairingCode = String(newValue.prefix(6))
                            }
                        }
                    Text("Run 'nova host pair-code' on your Windows PC to generate an ephemeral 5-minute PIN.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if let err = appModel.errorMessage {
                    Section {
                        Text(err)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                }

                Section {
                    Button {
                        Task { await performPairing() }
                    } label: {
                        if isPairing {
                            HStack {
                                Spacer()
                                ProgressView()
                                Spacer()
                            }
                        } else {
                            Text("Pair This Device")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .multilineTextAlignment(.center)
                        }
                    }
                    .disabled(pairingCode.count != 6 || isPairing)
                }
            }
            .navigationTitle("Link Windows PC")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        isPresented = false
                    }
                }
            }
        }
    }

    private func performPairing() async {
        isPairing = true
        let success = await appModel.pairDevice(
            hostUrl: hostUrl.trimmingCharacters(in: .whitespaces),
            pinCode: pairingCode.trimmingCharacters(in: .whitespaces),
            deviceName: UIDevice.current.name
        )
        isPairing = false
        if success {
            onPaired?()
            isPresented = false
        }
    }
}
