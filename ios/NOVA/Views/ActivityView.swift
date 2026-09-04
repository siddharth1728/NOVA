//
//  ActivityView.swift
//  NOVA iOS Control Center
//
//  Streaming event stream, audit trail, and host lifecycle activity monitor.
//

import SwiftUI

public struct ActivityView: View {
    @ObservedObject private var ws = WebSocketManager.shared
    @State private var isAutoScroll = true

    public init() {}

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Connection Status Header
                wsStatusHeader

                if ws.recentEvents.isEmpty {
                    emptyActivityState
                } else {
                    List {
                        ForEach(ws.recentEvents, id: \.self) { event in
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
                        ws.recentEvents.removeAll()
                    }
                }
            }
            .onAppear {
                if !ws.isConnected {
                    ws.connect()
                }
            }
        }
    }

    private var wsStatusHeader: some View {
        HStack {
            Circle()
                .fill(ws.isConnected ? Color.green : Color.orange)
                .frame(width: 8, height: 8)
            Text(ws.isConnected ? "WebSocket Stream Connected" : "Connecting to Host Stream...")
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
            Text("\(ws.recentEvents.count) Events")
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
            Text("Streaming telemetry ticks, agent plan events, and audit logs will appear here in real time.")
                .font(.caption)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 40)
            Spacer()
        }
    }
}
