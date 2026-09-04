//
//  ConnectionManager.swift
//  NOVA iOS Control Center
//
//  Authoritative app-wide connection state machine, background polling, and reconnect engine.
//

import Foundation
import Combine

public enum ConnectionState: String, Sendable {
    case disconnected = "DISCONNECTED"
    case connecting = "CONNECTING"
    case authenticating = "AUTHENTICATING"
    case connected = "CONNECTED"
    case degraded = "DEGRADED"
    case reconnecting = "RECONNECTING"
    case failed = "FAILED"
}

@MainActor
public final class NovaAppModel: ObservableObject {
    public static let shared = NovaAppModel()

    // Connection Lifecycle State
    @Published public var connectionState: ConnectionState = .disconnected
    @Published public var latencyMs: Int? = nil
    @Published public var hostHealth: HealthResponse? = nil
    @Published public var systemStatus: SystemStatus? = nil
    @Published public var capabilities: CapabilitiesMatrix? = nil

    // Task Execution State
    @Published public var activeTask: TaskRecord? = nil
    @Published public var isExecutingTask: Bool = false
    @Published public var lastQueryResponse: RemoteQueryResponse? = nil

    // Screen State
    @Published public var lastScreenshot: ScreenCaptureResponse? = nil
    @Published public var isCapturingScreen: Bool = false

    // Real-Time Event Stream
    @Published public var recentEvents: [String] = []
    @Published public var isWebSocketConnected: Bool = false

    // Authentication State
    @Published public var isPaired: Bool = KeychainStore.shared.isPaired
    @Published public var errorMessage: String? = nil

    private var pollTimer: Timer?
    private var reconnectAttempt = 0
    private var webSocketTask: URLSessionWebSocketTask?
    private var pingTimer: Timer?

    private init() {
        self.isPaired = KeychainStore.shared.isPaired
    }

    // MARK: - Connection Lifecycle

    public func startConnection() {
        guard isPaired else {
            self.connectionState = .disconnected
            return
        }

        Task {
            await establishConnection()
        }
    }

    public func establishConnection() async {
        self.connectionState = (reconnectAttempt > 0) ? .reconnecting : .connecting
        self.errorMessage = nil

        do {
            // 1. Health check & latency measurement
            let (health, latency) = try await NovaClient.shared.checkHealth()
            self.hostHealth = health
            self.latencyMs = latency

            // 2. Authentication check
            self.connectionState = .authenticating
            let status = try await NovaClient.shared.fetchStatus()
            self.systemStatus = status

            // 3. Capabilities matrix discovery
            let caps = try await NovaClient.shared.fetchCapabilities()
            self.capabilities = caps

            // 4. WebSocket connection
            connectWebSocket()

            self.connectionState = .connected
            self.reconnectAttempt = 0
            startPeriodicStatusPoll()

        } catch {
            print("Host connection failed: \(error)")
            self.errorMessage = error.localizedDescription
            self.connectionState = .failed
            scheduleReconnect()
        }
    }

    public func stopConnection() {
        pollTimer?.invalidate()
        pollTimer = nil
        disconnectWebSocket()
        self.connectionState = .disconnected
        self.latencyMs = nil
    }

    private func scheduleReconnect() {
        guard isPaired else { return }
        pollTimer?.invalidate()
        pollTimer = nil

        reconnectAttempt += 1
        // Exponential backoff capped at 15 seconds
        let delay = min(Double(1 << min(reconnectAttempt, 4)), 15.0)
        print("Scheduling reconnect attempt \(reconnectAttempt) in \(delay)s")

        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            Task { @MainActor in
                await self?.establishConnection()
            }
        }
    }

    private func startPeriodicStatusPoll() {
        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self, self.connectionState == .connected else { return }
                do {
                    let (health, latency) = try await NovaClient.shared.checkHealth()
                    self.hostHealth = health
                    self.latencyMs = latency

                    let status = try await NovaClient.shared.fetchStatus()
                    self.systemStatus = status
                } catch {
                    self.connectionState = .degraded
                    self.scheduleReconnect()
                }
            }
        }
    }

    // MARK: - Actions

    public func dispatchAgentTask(prompt: String) async {
        let trimmed = prompt.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }

        isExecutingTask = true
        errorMessage = nil

        let reqId = UUID().uuidString
        do {
            let resp = try await NovaClient.shared.sendAgentQuery(prompt: trimmed, requestId: reqId)
            self.lastQueryResponse = resp
            self.activeTask = nil
        } catch {
            self.errorMessage = error.localizedDescription
        }

        isExecutingTask = false
    }

    public func cancelCurrentTask() async {
        guard let task = activeTask else { return }
        do {
            _ = try await NovaClient.shared.cancelTask(taskId: task.taskId)
            self.activeTask = nil
            self.isExecutingTask = false
        } catch {
            self.errorMessage = "Failed to cancel task: \(error.localizedDescription)"
        }
    }

    public func captureDesktopSnapshot(maxWidth: Int? = 1280) async {
        isCapturingScreen = true
        errorMessage = nil
        do {
            let resp = try await NovaClient.shared.captureScreen(maxWidth: maxWidth)
            self.lastScreenshot = resp
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isCapturingScreen = false
    }

    public func emergencyLockWorkstation() async {
        do {
            _ = try await NovaClient.shared.lockWorkstation(dryRun: false)
        } catch {
            self.errorMessage = "Lock failed: \(error.localizedDescription)"
        }
    }

    public func pairDevice(hostUrl: String, pinCode: String, deviceName: String = "iPhone") async -> Bool {
        errorMessage = nil
        do {
            let resp = try await NovaClient.shared.pair(hostUrl: hostUrl, pairingCode: pinCode, deviceName: deviceName)
            self.isPaired = true
            print("Paired with host: \(resp.hostName)")
            await establishConnection()
            return true
        } catch {
            self.errorMessage = error.localizedDescription
            return false
        }
    }

    public func unpairDevice() {
        stopConnection()
        KeychainStore.shared.clearAll()
        self.isPaired = false
        self.hostHealth = nil
        self.systemStatus = nil
        self.capabilities = nil
        self.recentEvents.removeAll()
    }

    // MARK: - WebSocket Streaming

    private func connectWebSocket() {
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

        self.isWebSocketConnected = true
        startListeningWebSocket()
        startPingTimer()
    }

    private func disconnectWebSocket() {
        pingTimer?.invalidate()
        pingTimer = nil
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
        webSocketTask = nil
        self.isWebSocketConnected = false
    }

    private func startListeningWebSocket() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                guard let self = self else { return }
                switch result {
                case .success(let message):
                    switch message {
                    case .string(let text):
                        self.handleIncomingWebSocketText(text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self.handleIncomingWebSocketText(text)
                        }
                    @unknown default:
                        break
                    }
                    self.startListeningWebSocket()

                case .failure(let error):
                    print("WebSocket connection dropped: \(error)")
                    self.isWebSocketConnected = false
                    self.disconnectWebSocket()
                }
            }
        }
    }

    private func handleIncomingWebSocketText(_ text: String) {
        let timestamp = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
        self.recentEvents.insert("[\(timestamp)] \(text)", at: 0)
        if self.recentEvents.count > 100 {
            self.recentEvents.removeLast()
        }
    }

    private func startPingTimer() {
        pingTimer?.invalidate()
        pingTimer = Timer.scheduledTimer(withTimeInterval: 15.0, repeats: true) { [weak self] _ in
            self?.webSocketTask?.send(.string("{\"action\":\"ping\"}")) { _ in }
        }
    }
}
