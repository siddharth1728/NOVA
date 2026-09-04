//
//  ComputerView.swift
//  NOVA iOS Control Center
//
//  Real-time desktop screen capture, display inspection, and workstation lock control.
//

import SwiftUI

public struct ComputerView: View {
    @State private var screenData: ScreenCaptureResponse?
    @State private var uiImage: UIImage?
    @State private var isCapturing = false
    @State private var errorMessage: String?
    @State private var showLockConfirmation = false
    @State private var isLocking = false

    public init() {}

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Desktop Screen Canvas
                    screenCanvas

                    // Screen Metadata Details
                    if let meta = screenData {
                        metadataBar(meta)
                    }

                    if let err = errorMessage {
                        errorBanner(err)
                    }

                    // Workstation Remote Actions
                    controlsSection
                }
                .padding()
            }
            .navigationTitle("Computer View")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await captureScreen() }
                    } label: {
                        if isCapturing {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(isCapturing)
                }
            }
            .task {
                await captureScreen()
            }
        }
        .alert("Lock Windows Workstation?", isPresented: $showLockConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Lock PC Now", role: .destructive) {
                Task { await executeLock() }
            }
        } message: {
            Text("This will invoke Win32 LockWorkStation on your PC immediately, locking the active Windows session.")
        }
    }

    private var screenCanvas: some View {
        ZStack {
            Color.black
                .frame(height: 220)
                .clipShape(RoundedRectangle(cornerRadius: 16))

            if let img = uiImage {
                Image(uiImage: img)
                    .resizable()
                    .scaledToFit()
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                    .padding(4)
            } else if isCapturing {
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
                        .font(.system(size: 40))
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
        HStack {
            Label("\(data.width) × \(data.height)", systemImage: "aspectratio")
            Spacer()
            Label("\(data.fileSizeBytes / 1024) KB", systemImage: "doc")
            Spacer()
            Label(data.format.uppercased(), systemImage: "photo")
        }
        .font(.caption)
        .foregroundStyle(.secondary)
        .padding(.horizontal)
    }

    private var controlsSection: some View {
        VStack(spacing: 12) {
            Button {
                Task { await captureScreen() }
            } label: {
                Label("Capture Fresh Snapshot", systemImage: "camera.viewfinder")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .disabled(isCapturing)

            Button {
                showLockConfirmation = true
            } label: {
                Label("Lock Workstation", systemImage: "lock.shield.fill")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.red.opacity(0.15))
                    .foregroundStyle(.red)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .disabled(isLocking)
        }
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

    private func captureScreen() async {
        isCapturing = true
        errorMessage = nil
        do {
            let resp = try await NovaClient.shared.captureScreen(maxWidth: 1280)
            self.screenData = resp
            if let decodedData = Data(base64Encoded: resp.imageBase64) {
                self.uiImage = UIImage(data: decodedData)
            }
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isCapturing = false
    }

    private func executeLock() async {
        isLocking = true
        do {
            _ = try await NovaClient.shared.lockWorkstation(dryRun: false)
        } catch {
            self.errorMessage = "Lock failed: \(error.localizedDescription)"
        }
        isLocking = false
    }
}
