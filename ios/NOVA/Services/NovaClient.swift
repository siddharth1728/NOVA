//
//  NovaClient.swift
//  NOVA iOS Control Center
//
//  Authoritative async HTTP REST client for communicating with the Windows NOVA Host.
//

import Foundation

public enum NovaClientError: Error, LocalizedError {
    case unauthenticated
    case deviceRevoked
    case invalidHostUrl
    case taskNotFound
    case taskCancelled
    case serverError(String)
    case networkError(Error)

    public var errorDescription: String? {
        switch self {
        case .unauthenticated:
            return "Device is unauthenticated or token expired. Please re-pair."
        case .deviceRevoked:
            return "This device has been revoked by the Windows host."
        case .invalidHostUrl:
            return "Invalid host URL configured."
        case .taskNotFound:
            return "Requested task was not found or already completed."
        case .taskCancelled:
            return "Task was cancelled before completion."
        case .serverError(let msg):
            return "Host error: \(msg)"
        case .networkError(let err):
            return "Network connection failed: \(err.localizedDescription)"
        }
    }
}

public final class NovaClient: Sendable {
    public static let shared = NovaClient()
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    private var baseUrl: URL? {
        URL(string: KeychainStore.shared.hostBaseUrl)
    }

    private func makeRequest(endpoint: String, method: String = "GET", body: Data? = nil) throws -> URLRequest {
        guard let base = baseUrl else {
            throw NovaClientError.invalidHostUrl
        }
        let url = base.appendingPathComponent(endpoint)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainStore.shared.authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = body
        return request
    }

    public func checkHealth() async throws -> (HealthResponse, Int) {
        let startTime = CFAbsoluteTimeGetCurrent()
        let req = try makeRequest(endpoint: "/api/v1/health")
        let (data, response) = try await session.data(for: req)
        let latencyMs = Int((CFAbsoluteTimeGetCurrent() - startTime) * 1000)
        try checkHttpResponse(response, data: data)
        let health = try JSONDecoder().decode(HealthResponse.self, from: data)
        return (health, latencyMs)
    }

    public func pair(hostUrl: String, pairingCode: String, deviceName: String = "iPhone") async throws -> PairingResponse {
        KeychainStore.shared.hostBaseUrl = hostUrl
        guard let base = baseUrl else {
            throw NovaClientError.invalidHostUrl
        }

        let url = base.appendingPathComponent("/api/v1/pair")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload = PairingRequest(
            pairingCode: pairingCode,
            deviceId: KeychainStore.shared.deviceId,
            deviceName: deviceName,
            platform: "iOS"
        )
        request.httpBody = try JSONEncoder().encode(payload)

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw NovaClientError.serverError("Non-HTTP response received")
        }

        if http.statusCode == 200 {
            let res = try JSONDecoder().decode(PairingResponse.self, from: data)
            KeychainStore.shared.authToken = res.token
            return res
        } else {
            if let err = try? JSONDecoder().decode(ProtocolErrorResponse.self, from: data) {
                throw NovaClientError.serverError(err.error.message)
            }
            throw NovaClientError.serverError("Pairing failed with status \(http.statusCode)")
        }
    }

    public func fetchStatus() async throws -> SystemStatus {
        let req = try makeRequest(endpoint: "/api/v1/status")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(SystemStatus.self, from: data)
    }

    public func captureScreen(maxWidth: Int? = 1280) async throws -> ScreenCaptureResponse {
        let reqPayload = ScreenCaptureRequest(format: "png", maxWidth: maxWidth)
        let bodyData = try JSONEncoder().encode(reqPayload)
        let req = try makeRequest(endpoint: "/api/v1/screen/capture", method: "POST", body: bodyData)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(ScreenCaptureResponse.self, from: data)
    }

    public func fetchCapabilities() async throws -> CapabilitiesMatrix {
        let req = try makeRequest(endpoint: "/api/v1/capabilities")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(CapabilitiesMatrix.self, from: data)
    }

    public func sendAgentQuery(prompt: String, requestId: String? = nil) async throws -> RemoteQueryResponse {
        let reqId = requestId ?? UUID().uuidString
        let reqPayload = RemoteQueryRequest(query: prompt, requestId: reqId)
        let bodyData = try JSONEncoder().encode(reqPayload)
        let req = try makeRequest(endpoint: "/api/v1/agent/query", method: "POST", body: bodyData)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(RemoteQueryResponse.self, from: data)
    }

    public func cancelTask(taskId: String, reason: String = "User cancelled from iOS") async throws -> TaskCancelResponse {
        let reqPayload = TaskCancelRequest(taskId: taskId, reason: reason)
        let bodyData = try JSONEncoder().encode(reqPayload)
        let req = try makeRequest(endpoint: "/api/v1/agent/tasks/\(taskId)/cancel", method: "POST", body: bodyData)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskCancelResponse.self, from: data)
    }

    public func fetchTask(taskId: String) async throws -> TaskRecord {
        let req = try makeRequest(endpoint: "/api/v1/agent/tasks/\(taskId)")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskRecord.self, from: data)
    }

    public func lockWorkstation(dryRun: Bool = false) async throws -> EmergencyActionResponse {
        let endpoint = dryRun ? "/api/v1/emergency/lock?dry_run=true" : "/api/v1/emergency/lock"
        let reqPayload = EmergencyActionRequest(action: "LOCK_WORKSTATION")
        let bodyData = try JSONEncoder().encode(reqPayload)
        let req = try makeRequest(endpoint: endpoint, method: "POST", body: bodyData)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(EmergencyActionResponse.self, from: data)
    }

    // =========================================================================
    // Phase 05: Computer Control Client Methods
    // =========================================================================

    public func listWindows(visibleOnly: Bool = true) async throws -> [WindowInfo] {
        let req = try makeRequest(endpoint: "/api/v1/computer/windows?visible_only=\(visibleOnly)")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode([WindowInfo].self, from: data)
    }

    public func focusWindow(hwnd: Int) async throws {
        let payload = WindowFocusRequest(hwnd: hwnd)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/windows/focus", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func closeWindow(hwnd: Int) async throws {
        let payload = WindowCloseRequest(hwnd: hwnd)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/windows/close", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func listApps(search: String? = nil) async throws -> [AppInfo] {
        var ep = "/api/v1/computer/apps"
        if let s = search, !s.isEmpty, let enc = s.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
            ep += "?search=\(enc)"
        }
        let req = try makeRequest(endpoint: ep)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode([AppInfo].self, from: data)
    }

    public func launchApp(appNameOrPath: String) async throws -> AppLaunchResponse {
        let payload = AppLaunchRequest(appNameOrPath: appNameOrPath)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/apps/launch", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(AppLaunchResponse.self, from: data)
    }

    public func sendMouseMove(x: Int, y: Int) async throws {
        let payload = MouseMoveRequest(x: x, y: y)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/mouse/move", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func sendMouseClick(button: String = "left", count: Int = 1, x: Int? = nil, y: Int? = nil) async throws {
        let payload = MouseClickRequest(button: button, count: count, x: x, y: y)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/mouse/click", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func sendMouseScroll(clicks: Int) async throws {
        let payload = MouseScrollRequest(clicks: clicks)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/mouse/scroll", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func sendKeyboardType(text: String) async throws {
        let payload = KeyboardTypeRequest(text: text)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/keyboard/type", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func sendKeyPress(key: String) async throws {
        let payload = KeyPressRequest(key: key)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/keyboard/press", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func sendKeyCombo(keys: [String]) async throws {
        let payload = KeyComboRequest(keys: keys, targetHwnd: nil)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/keyboard/press", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
    }

    public func listProcesses(search: String? = nil, top: Int = 50) async throws -> [ProcessInfo] {
        var ep = "/api/v1/computer/processes?top=\(top)"
        if let s = search, !s.isEmpty, let enc = s.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
            ep += "&search=\(enc)"
        }
        let req = try makeRequest(endpoint: ep)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode([ProcessInfo].self, from: data)
    }

    public func stopProcess(pid: Int, force: Bool = false) async throws -> ProcessStopResponse {
        let payload = ProcessStopRequest(force: force)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/computer/processes/\(pid)/stop", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(ProcessStopResponse.self, from: data)
    }

    // MARK: - Browser Subsystem API (Phase 08)

    public func getBrowserStatus() async throws -> BrowserStatusResponse {
        let req = try makeRequest(endpoint: "/api/v1/browser/status")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(BrowserStatusResponse.self, from: data)
    }

    public func listBrowserTabs() async throws -> [BrowserTabItem] {
        let req = try makeRequest(endpoint: "/api/v1/browser/tabs")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode([BrowserTabItem].self, from: data)
    }

    public func createBrowserTab(url: String?) async throws -> BrowserTabItem {
        let payload = BrowserNewTabRequest(url: url)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/browser/tabs", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(BrowserTabItem.self, from: data)
    }

    public func focusBrowserTab(tabId: String) async throws -> Bool {
        let req = try makeRequest(endpoint: "/api/v1/browser/tabs/\(tabId)/focus", method: "POST")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        let res = try JSONDecoder().decode(BrowserTabActionResponse.self, from: data)
        return res.success
    }

    public func closeBrowserTab(tabId: String) async throws -> Bool {
        let req = try makeRequest(endpoint: "/api/v1/browser/tabs/\(tabId)", method: "DELETE")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        let res = try JSONDecoder().decode(BrowserTabActionResponse.self, from: data)
        return res.success
    }

    // =========================================================================
    // Phase 09: Task Orchestration API
    // =========================================================================

    public func createOrchestratedTask(query: String, requestId: String? = nil, requireApproval: Bool = false, riskCeiling: String = "MEDIUM") async throws -> TaskDetailResponse {
        let payload = TaskCreateRequest(query: query, requestId: requestId, requireApproval: requireApproval, riskCeiling: riskCeiling)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/tasks", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskDetailResponse.self, from: data)
    }

    public func listOrchestratedTasks(status: String? = nil, limit: Int = 50) async throws -> [TaskDetailResponse] {
        var endpoint = "/api/v1/tasks?limit=\(limit)"
        if let status = status {
            endpoint += "&status=\(status)"
        }
        let req = try makeRequest(endpoint: endpoint, method: "GET")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode([TaskDetailResponse].self, from: data)
    }

    public func getOrchestratedTask(taskId: String) async throws -> TaskDetailResponse {
        let req = try makeRequest(endpoint: "/api/v1/tasks/\(taskId)", method: "GET")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskDetailResponse.self, from: data)
    }

    public func pauseOrchestratedTask(taskId: String, reason: String = "User paused from iOS") async throws -> TaskActionResponse {
        let payload = TaskActionRequest(reason: reason)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/tasks/\(taskId)/pause", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskActionResponse.self, from: data)
    }

    public func resumeOrchestratedTask(taskId: String) async throws -> TaskActionResponse {
        let req = try makeRequest(endpoint: "/api/v1/tasks/\(taskId)/resume", method: "POST")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskActionResponse.self, from: data)
    }

    public func cancelOrchestratedTask(taskId: String, reason: String = "User cancelled from iOS") async throws -> TaskActionResponse {
        let payload = TaskActionRequest(reason: reason)
        let body = try JSONEncoder().encode(payload)
        let req = try makeRequest(endpoint: "/api/v1/tasks/\(taskId)/cancel", method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskActionResponse.self, from: data)
    }

    public func getOrchestratedTaskSteps(taskId: String) async throws -> TaskStepsListResponse {
        let req = try makeRequest(endpoint: "/api/v1/tasks/\(taskId)/steps", method: "GET")
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(TaskStepsListResponse.self, from: data)
    }

    public func approveOrchestratedTaskStep(taskId: String, stepId: Int, approved: Bool, reason: String? = nil) async throws -> StepApprovalRemoteResponse {
        let payload = StepApprovalRemoteRequest(stepId: stepId, approved: approved, reason: reason)
        let body = try JSONEncoder().encode(payload)
        let endpoint = approved ? "/api/v1/tasks/\(taskId)/approve" : "/api/v1/tasks/\(taskId)/deny"
        let req = try makeRequest(endpoint: endpoint, method: "POST", body: body)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(StepApprovalRemoteResponse.self, from: data)
    }

    private func checkHttpResponse(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            throw NovaClientError.serverError("Non-HTTP response")
        }

        if http.statusCode == 401 {
            throw NovaClientError.unauthenticated
        } else if http.statusCode == 403 {
            if let err = try? JSONDecoder().decode(ProtocolErrorResponse.self, from: data),
               err.error.code == "REVOKED_DEVICE" {
                throw NovaClientError.deviceRevoked
            }
            throw NovaClientError.serverError("Forbidden action")
        } else if http.statusCode == 404 {
            throw NovaClientError.taskNotFound
        } else if http.statusCode == 499 {
            throw NovaClientError.taskCancelled
        } else if http.statusCode >= 400 {
            if let err = try? JSONDecoder().decode(ProtocolErrorResponse.self, from: data) {
                throw NovaClientError.serverError(err.error.message)
            }
            throw NovaClientError.serverError("HTTP \(http.statusCode)")
        }
    }
}
