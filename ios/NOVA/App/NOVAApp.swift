//
//  NOVAApp.swift
//  NOVA iOS Control Center
//
//  Application entry point and root scene for NOVA on iOS.
//

import SwiftUI

@main
struct NOVAApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @ObservedObject private var appModel = NovaAppModel.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .onChange(of: scenePhase) { _, newPhase in
                    switch newPhase {
                    case .active:
                        appModel.handleAppDidBecomeActive()
                    case .background:
                        appModel.handleAppDidEnterBackground()
                    default:
                        break
                    }
                }
        }
    }
}

public struct RootView: View {
    @ObservedObject private var appModel = NovaAppModel.shared
    @State private var showInitialSplash = true
    @State private var showPairingSheet = false

    public init() {}

    public var body: some View {
        ZStack {
            MainTabView()
                .opacity(showInitialSplash ? 0 : 1)

            if showInitialSplash {
                splashScreen
                    .transition(.opacity.combined(with: .scale(scale: 0.98)))
            }
        }
        .sheet(isPresented: $showPairingSheet) {
            PairingView(isPresented: $showPairingSheet)
        }
        .task {
            // Initial connection check
            appModel.handleAppDidBecomeActive()
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            withAnimation(.easeInOut(duration: 0.4)) {
                showInitialSplash = false
            }
            if !appModel.isPaired {
                showPairingSheet = true
            }
        }
    }

    private var splashScreen: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 24) {
                Spacer()

                ZStack {
                    Circle()
                        .fill(RadialGradient(
                            colors: [Color.cyan.opacity(0.35), Color.purple.opacity(0.2), Color.clear],
                            center: .center,
                            startRadius: 20,
                            endRadius: 100
                        ))
                        .frame(width: 180, height: 180)

                    Image(systemName: "star.circle.fill")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 84, height: 84)
                        .foregroundStyle(LinearGradient(
                            colors: [Color.cyan, Color.purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ))
                }

                VStack(spacing: 8) {
                    Text("NOVA")
                        .font(.system(size: 40, weight: .black, design: .rounded))
                        .foregroundStyle(LinearGradient(
                            colors: [.white, Color(.systemGray3)],
                            startPoint: .top,
                            endPoint: .bottom
                        ))
                        .tracking(3)

                    Text("Personal AI Computing Engine")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(.secondary)
                }

                Spacer()

                VStack(spacing: 12) {
                    ProgressView()
                        .tint(.cyan)

                    Text(appModel.isPaired ? "Checking workstation connection..." : "Preparing workstation pairing...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 40)
            }
        }
    }
}
