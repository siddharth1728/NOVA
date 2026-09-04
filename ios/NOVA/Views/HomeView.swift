//
//  HomeView.swift
//  NOVA iOS Control Center
//
//  Dashboard overview showing real-time Windows PC telemetry, latency, agent health, and quick actions.
//

import SwiftUI

public struct HomeView: View {
    @ObservedObject private var appModel = NovaAppModel.shared

    public init() {}

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Host Connection Card with Latency
                    connectionHeader

                    if let err = appModel.errorMessage {
                        errorBanner(err)
                    }

                    if let s = appModel.systemStatus {
                        // Hardware Resource Metrics
                        telemetryGauges(s.system)

                        // Agent Runtime Status
                        agentCard(s.agent)

                        // Quick Actions (Verified against capabilities)
                        quickActionsGrid
                    } else if appModel.connectionState == .connecting || appModel.connectionState == .authenticating {
                        ProgressView("Connecting to Windows Host...")
                            .padding(.top, 40)
                    } else {
                        unpairedOrOfflineCard
                    }
                }
                .padding()
            }
            .navigationTitle("NOVA Control Center")
            .refreshable {
                await appModel.establishConnection()
            }
            .task {
                if appModel.connectionState == .disconnected {
                    appModel.startConnection()
                }
            }
        }
    }

    private var connectionHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(appModel.systemStatus?.system.hostname ?? appModel.hostHealth?.hostName ?? "Windows Workstation")
                    .font(.title2.bold())
                Text(appModel.systemStatus?.system.osVersion ?? "Host Disconnected")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(stateColor)
                        .frame(width: 10, height: 10)
                    Text(stateTitle)
                        .font(.subheadline.bold())
                        .foregroundStyle(stateColor)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color(.secondarySystemBackground))
                .clipShape(Capsule())

                if let latency = appModel.latencyMs {
                    Text("\(latency) ms")
                        .font(.caption2.bold())
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var stateColor: Color {
        switch appModel.connectionState {
        case .connected: return .green
        case .connecting, .authenticating, .reconnecting: return .blue
        case .degraded: return .orange
        case .disconnected, .failed: return .red
        }
    }

    private var stateTitle: String {
        switch appModel.connectionState {
        case .connected: return "Online"
        case .connecting: return "Connecting"
        case .authenticating: return "Authenticating"
        case .reconnecting: return "Reconnecting"
        case .degraded: return "Degraded"
        case .disconnected: return "Offline"
        case .failed: return "Failed"
        }
    }

    private func telemetryGauges(_ metrics: SystemMetrics) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Host Telemetry")
                .font(.headline)

            HStack(spacing: 12) {
                metricBox(title: "CPU", value: "\(Int(metrics.cpuPercent))%", sub: "Live", color: .blue)
                metricBox(title: "RAM", value: "\(Int(metrics.ramPercent))%", sub: "\(metrics.ramUsedGb)/\(metrics.ramTotalGb) GB", color: .purple)
                metricBox(title: "Disk", value: "\(Int(metrics.diskPercent))%", sub: "\(metrics.diskUsedGb)/\(metrics.diskTotalGb) GB", color: .orange)
            }

            HStack {
                Text("Host Uptime:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("\(Int(metrics.uptimeSeconds / 3600))h \(Int((metrics.uptimeSeconds.truncatingRemainder(dividingBy: 3600)) / 60))m")
                    .font(.caption.bold())
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private func metricBox(title: String, value: String, sub: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title2.bold())
                .foregroundStyle(color)
            Text(sub)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.tertiarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func agentCard(_ agent: AgentStatus) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("NOVA Agent Runtime")
                    .font(.headline)
                Spacer()
                Text(agent.state)
                    .font(.caption.bold())
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(agent.state == "IDLE" ? Color.green.opacity(0.2) : Color.blue.opacity(0.2))
                    .foregroundStyle(agent.state == "IDLE" ? Color.green : Color.blue)
                    .clipShape(Capsule())
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Workspace Root: \(agent.workspaceRoot)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("Registered Safety Tools: \(agent.toolsRegistered)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var quickActionsGrid: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Quick Commands")
                .font(.headline)

            HStack(spacing: 12) {
                if hasCapability("workstation_lock") {
                    Button {
                        Task { await appModel.emergencyLockWorkstation() }
                    } label: {
                        Label("Lock PC", systemImage: "lock.fill")
                            .font(.subheadline.bold())
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.red.opacity(0.15))
                            .foregroundStyle(.red)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }

                if hasCapability("desktop_screen_capture") {
                    Button {
                        Task { await appModel.captureDesktopSnapshot() }
                    } label: {
                        Label("Snapshot", systemImage: "camera.viewfinder")
                            .font(.subheadline.bold())
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.blue.opacity(0.15))
                            .foregroundStyle(.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }

                Button {
                    Task { await appModel.establishConnection() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .foregroundStyle(.primary)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private func hasCapability(_ name: String) -> Bool {
        guard let caps = appModel.capabilities else { return true }
        return caps.capabilities.contains(where: { $0.name == name && $0.available })
    }

    private var unpairedOrOfflineCard: some View {
        VStack(spacing: 12) {
            Image(systemName: "desktopcomputer.trianglebadge.exclamationmark")
                .font(.system(size: 40))
                .foregroundStyle(.secondary)
            Text("Workstation Disconnected")
                .font(.headline)
            Text("Ensure NOVA Windows Host is running ('nova host start') and your iPhone is paired.")
                .font(.caption)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Reconnect Now") {
                Task { await appModel.establishConnection() }
            }
            .buttonStyle(.borderedProminent)
            .padding(.top, 4)
        }
        .padding(30)
        .frame(maxWidth: .infinity)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
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
}
