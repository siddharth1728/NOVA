//
//  HomeView.swift
//  NOVA iOS Control Center
//
//  Dashboard overview showing real-time Windows PC telemetry, agent health, and quick actions.
//

import SwiftUI

public struct HomeView: View {
    @State private var status: SystemStatus?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @ObservedObject private var ws = WebSocketManager.shared

    public init() {}

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Host Connection Card
                    connectionHeader

                    if let err = errorMessage {
                        errorBanner(err)
                    }

                    if let s = status {
                        // Hardware Resource Metrics
                        telemetryGauges(s.system)

                        // Agent Runtime Status
                        agentCard(s.agent)

                        // Quick Actions
                        quickActionsGrid
                    } else if isLoading {
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
                await refreshData()
            }
            .task {
                await refreshData()
            }
        }
    }

    private var connectionHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(status?.system.hostname ?? "Windows PC")
                    .font(.title2.bold())
                Text(status?.system.osVersion ?? "Host Disconnected")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            HStack(spacing: 6) {
                Circle()
                    .fill(status != nil ? Color.green : Color.red)
                    .frame(width: 10, height: 10)
                Text(status != nil ? "Online" : "Offline")
                    .font(.subheadline.bold())
                    .foregroundStyle(status != nil ? .green : .red)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color(.secondarySystemBackground))
            .clipShape(Capsule())
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
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
                Button {
                    Task { await lockWorkstationAction() }
                } label: {
                    Label("Lock PC", systemImage: "lock.fill")
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.red.opacity(0.15))
                        .foregroundStyle(.red)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }

                Button {
                    Task { await refreshData() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue.opacity(0.15))
                        .foregroundStyle(.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private var unpairedOrOfflineCard: some View {
        VStack(spacing: 12) {
            Image(systemName: "desktopcomputer.trianglebadge.exclamationmark")
                .font(.system(size: 40))
                .foregroundStyle(.secondary)
            Text("Workstation Unreachable")
                .font(.headline)
            Text("Ensure NOVA Windows Host is running ('nova host start') and your device is paired in Settings.")
                .font(.caption)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Retry Connection") {
                Task { await refreshData() }
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

    private func refreshData() async {
        isLoading = true
        errorMessage = nil
        do {
            let res = try await NovaClient.shared.fetchStatus()
            self.status = res
        } catch {
            self.errorMessage = error.localizedDescription
            self.status = nil
        }
        isLoading = false
    }

    private func lockWorkstationAction() async {
        do {
            _ = try await NovaClient.shared.lockWorkstation(dryRun: false)
        } catch {
            self.errorMessage = "Lock failed: \(error.localizedDescription)"
        }
    }
}
