//
//  ActivityView.swift
//  NOVA iOS Control Center
//
//  Streaming event log, audit trail, and host lifecycle activity monitor.
//

import SwiftUI

public struct ActivityView: View {
    @ObservedObject private var appModel = NovaAppModel.shared

    public init() {}

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Connection Status Header
                wsStatusHeader

                if appModel.recentEvents.isEmpty {
                    emptyActivityState
                } else {
                    List {
                        ForEach(appModel.recentEvents, id: \.self) { event in
                            Text(event)
                                .font(.system(.caption, design: .monospaced))
                                .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Live Activity")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear") {
                        appModel.recentEvents.removeAll()
                    }
                }
            }
        }
    }

    private var wsStatusHeader: some View {
        HStack {
            Circle()
                .fill(appModel.isWebSocketConnected ? Color.green : Color.orange)
                .frame(width: 8, height: 8)
            Text(appModel.isWebSocketConnected ? "WebSocket Stream Connected" : "Connecting to Host Stream...")
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
            Text("\(appModel.recentEvents.count) Events")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(.secondarySystemBackground))
    }

    private var emptyActivityState: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "waveform.path.ecg")
                .font(.system(size: 40))
                .foregroundStyle(.secondary)
            Text("No Streaming Events")
                .font(.headline)
            Text("Real-time telemetry ticks, agent plan events, task cancellations, and audit logs stream here via WebSockets.")
                .font(.caption)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 40)
            Spacer()
        }
    }
}
