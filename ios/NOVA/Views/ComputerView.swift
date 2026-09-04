//
//  ComputerView.swift
//  NOVA iOS Control Center
//
//  Desktop screen capture inspection, frame metadata, and emergency workstation lock.
//

import SwiftUI

public struct ComputerView: View {
    @ObservedObject private var appModel = NovaAppModel.shared
    @State private var uiImage: UIImage?
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
                    if let meta = appModel.lastScreenshot {
                        metadataBar(meta)
                    }

                    if let err = appModel.errorMessage {
                        errorBanner(err)
                    }

                    // Workstation Actions
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
            }
        }
        .alert("Lock Windows Workstation?", isPresented: $showLockConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Lock PC Now", role: .destructive) {
                Task { await executeLock() }
            }
        } message: {
            Text("This will invoke Win32 LockWorkStation on your PC immediately, securing the active Windows session.")
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
            .disabled(appModel.isCapturingScreen)

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
        await appModel.captureDesktopSnapshot(maxWidth: 1280)
        if let b64 = appModel.lastScreenshot?.imageBase64, let data = Data(base64Encoded: b64) {
            self.uiImage = UIImage(data: data)
        }
    }

    private func executeLock() async {
        isLocking = true
        await appModel.emergencyLockWorkstation()
        isLocking = false
    }
}
