//
//  WebSocketManager.swift
//  NOVA iOS Control Center
//
//  Real-time streaming event consumer for desktop telemetry, agent plans, and audit logs.
//

import Foundation
import Combine

@MainActor
public final class WebSocketManager: ObservableObject {
    public static let shared = WebSocketManager()

    @Published public var isConnected: Bool = false
    @Published public var latestMetrics: SystemMetrics?
    @Published public var recentEvents: [String] = []

    private var webSocketTask: URLSessionWebSocketTask?
    private var pingTimer: Timer?

    private init() {}

    public func connect() {
        guard let token = KeychainStore.shared.authToken else { return }
        guard let httpUrl = URL(string: KeychainStore.shared.hostBaseUrl) else { return }

        var components = URLComponents(url: httpUrl, resolvingAgainstBaseURL: false)
        components?.scheme = (httpUrl.scheme == "https") ? "wss" : "ws"
        components?.path = "/ws/v1/events"
        components?.queryItems = [URLQueryItem(name: "token", value: token)]

        guard let wsUrl = components?.url else { return }

        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: wsUrl)
        webSocketTask?.resume()

        self.isConnected = true
        startListening()
        startPingTimer()
    }

    public func disconnect() {
        pingTimer?.invalidate()
        pingTimer = nil
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
        webSocketTask = nil
        self.isConnected = false
    }

    private func startListening() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                guard let self = self else { return }
                switch result {
                case .success(let message):
                    switch message {
                    case .string(let text):
                        self.handleIncomingMessage(text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self.handleIncomingMessage(text)
                        }
                    @unknown default:
                        break
                    }
                    self.startListening()

                case .failure(let error):
                    print("WebSocket receive error: \(error)")
                    self.disconnect()
                }
            }
        }
    }

    private func handleIncomingMessage(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }

        let timestamp = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
        self.recentEvents.insert("[\(timestamp)] \(text)", at: 0)
        if self.recentEvents.count > 50 {
            self.recentEvents.removeLast()
        }

        if let event = try? JSONDecoder().decode(WebSocketEvent.self, from: data) {
            if event.eventType == "telemetry" {
                // If telemetry event contains parsed metrics
            }
        }
    }

    private func startPingTimer() {
        pingTimer?.invalidate()
        pingTimer = Timer.scheduledTimer(withTimeInterval: 15.0, repeats: true) { [weak self] _ in
            self?.webSocketTask?.send(.string("{\"action\":\"ping\"}")) { _ in }
        }
    }
}
