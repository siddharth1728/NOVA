//
//  ProtocolModels.swift
//  NOVA iOS Control Center
//
//  Shared typed data models corresponding to NOVA Remote Protocol v1.
//

import Foundation

public let PROTOCOL_VERSION = "1.0.0"
public let SERVER_VERSION = "0.4.0"

public enum DeviceRole: String, Codable, Sendable {
    case controller = "CONTROLLER"
    case observer = "OBSERVER"
    case admin = "ADMIN"
}

public enum DeviceStatus: String, Codable, Sendable {
    case pending = "PENDING"
    case active = "ACTIVE"
    case revoked = "REVOKED"
}

public enum TaskStatus: String, Codable, Sendable {
    case queued = "QUEUED"
    case planning = "PLANNING"
    case waitingForApproval = "WAITING_FOR_APPROVAL"
    case executing = "EXECUTING"
    case verifying = "VERIFYING"
    case completed = "COMPLETED"
    case failed = "FAILED"
    case cancelled = "CANCELLED"
    case disconnected = "DISCONNECTED"
}

public struct PairingRequest: Codable, Sendable {
    public let pairingCode: String
    public let deviceId: String
    public let deviceName: String
    public let platform: String
    public let clientVersion: String

    public init(pairingCode: String, deviceId: String, deviceName: String, platform: String = "iOS", clientVersion: String = "0.4.0") {
        self.pairingCode = pairingCode
        self.deviceId = deviceId
        self.deviceName = deviceName
        self.platform = platform
        self.clientVersion = clientVersion
    }

    enum CodingKeys: String, CodingKey {
        case pairingCode = "pairing_code"
        case deviceId = "device_id"
        case deviceName = "device_name"
        case platform
        case clientVersion = "client_version"
    }
}

public struct PairingResponse: Codable, Sendable {
    public let token: String
    public let deviceId: String
    public let hostName: String
    public let serverVersion: String
    public let protocolVersion: String
    public let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case token
        case deviceId = "device_id"
        case hostName = "host_name"
        case serverVersion = "server_version"
        case protocolVersion = "protocol_version"
        case expiresAt = "expires_at"
    }
}

public struct HealthResponse: Codable, Sendable {
    public let status: String
    public let hostName: String
    public let serverVersion: String
    public let protocolVersion: String
    public let uptimeSeconds: Double
    public let agentState: String
    public let activeTasksCount: Int
    public let timestamp: String

    enum CodingKeys: String, CodingKey {
        case status
        case hostName = "host_name"
        case serverVersion = "server_version"
        case protocolVersion = "protocol_version"
        case uptimeSeconds = "uptime_seconds"
        case agentState = "agent_state"
        case activeTasksCount = "active_tasks_count"
        case timestamp
    }
}

public struct SystemMetrics: Codable, Sendable {
    public let cpuPercent: Double
    public let ramTotalGb: Double
    public let ramUsedGb: Double
    public let ramPercent: Double
    public let diskTotalGb: Double
    public let diskUsedGb: Double
    public let diskPercent: Double
    public let uptimeSeconds: Double
    public let bootTime: String
    public let osVersion: String
    public let hostname: String

    enum CodingKeys: String, CodingKey {
        case cpuPercent = "cpu_percent"
        case ramTotalGb = "ram_total_gb"
        case ramUsedGb = "ram_used_gb"
        case ramPercent = "ram_percent"
        case diskTotalGb = "disk_total_gb"
        case diskUsedGb = "disk_used_gb"
        case diskPercent = "disk_percent"
        case uptimeSeconds = "uptime_seconds"
        case bootTime = "boot_time"
        case osVersion = "os_version"
        case hostname
    }
}

public struct AgentStatus: Codable, Sendable {
    public let state: String
    public let activePlanId: String?
    public let workspaceRoot: String
    public let toolsRegistered: Int
    public let uptimeSeconds: Double

    enum CodingKeys: String, CodingKey {
        case state
        case activePlanId = "active_plan_id"
        case workspaceRoot = "workspace_root"
        case toolsRegistered = "tools_registered"
        case uptimeSeconds = "uptime_seconds"
    }
}

public struct SystemStatus: Codable, Sendable {
    public let timestamp: String
    public let protocolVersion: String
    public let system: SystemMetrics
    public let agent: AgentStatus

    enum CodingKeys: String, CodingKey {
        case timestamp
        case protocolVersion = "protocol_version"
        case system
        case agent
    }
}

public struct ScreenCaptureRequest: Codable, Sendable {
    public let format: String
    public let maxWidth: Int?
    public let maxHeight: Int?
    public let quality: Int

    public init(format: String = "png", maxWidth: Int? = nil, maxHeight: Int? = nil, quality: Int = 80) {
        self.format = format
        self.maxWidth = maxWidth
        self.maxHeight = maxHeight
        self.quality = quality
    }

    enum CodingKeys: String, CodingKey {
        case format
        case maxWidth = "max_width"
        case maxHeight = "max_height"
        case quality
    }
}

public struct ScreenCaptureResponse: Codable, Sendable {
    public let timestamp: String
    public let format: String
    public let width: Int
    public let height: Int
    public let imageBase64: String
    public let fileSizeBytes: Int

    enum CodingKeys: String, CodingKey {
        case timestamp
        case format
        case width
        case height
        case imageBase64 = "image_base64"
        case fileSizeBytes = "file_size_bytes"
    }
}

public struct CapabilityInfo: Codable, Sendable, Identifiable {
    public var id: String { name }
    public let name: String
    public let available: Bool
    public let riskLevel: String
    public let description: String
    public let category: String?

    public init(name: String, available: Bool, riskLevel: String, description: String, category: String? = nil) {
        self.name = name
        self.available = available
        self.riskLevel = riskLevel
        self.description = description
        self.category = category
    }

    enum CodingKeys: String, CodingKey {
        case name
        case available
        case riskLevel = "risk_level"
        case description
        case category
    }
}


public struct CapabilitiesMatrix: Codable, Sendable {
    public let version: String
    public let protocolVersion: String
    public let hostPlatform: String
    public let capabilities: [CapabilityInfo]

    enum CodingKeys: String, CodingKey {
        case version
        case protocolVersion = "protocol_version"
        case hostPlatform = "host_platform"
        case capabilities
    }
}

public struct RemoteQueryRequest: Codable, Sendable {
    public let query: String
    public let requestId: String?
    public let requireApproval: Bool
    public let maxSteps: Int

    public init(query: String, requestId: String? = nil, requireApproval: Bool = false, maxSteps: Int = 10) {
        self.query = query
        self.requestId = requestId
        self.requireApproval = requireApproval
        self.maxSteps = maxSteps
    }

    enum CodingKeys: String, CodingKey {
        case query
        case requestId = "request_id"
        case requireApproval = "require_approval"
        case maxSteps = "max_steps"
    }
}

public struct RemoteQueryResponse: Codable, Sendable {
    public let sessionId: String
    public let taskId: String
    public let requestId: String?
    public let query: String
    public let status: TaskStatus
    public let responseText: String
    public let toolCallsCount: Int
    public let stepsExecuted: Int
    public let verificationPassed: Bool
    public let planId: String?
    public let protocolVersion: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case taskId = "task_id"
        case requestId = "request_id"
        case query
        case status
        case responseText = "response_text"
        case toolCallsCount = "tool_calls_count"
        case stepsExecuted = "steps_executed"
        case verificationPassed = "verification_passed"
        case planId = "plan_id"
        case protocolVersion = "protocol_version"
    }
}

public struct TaskCancelRequest: Codable, Sendable {
    public let taskId: String
    public let reason: String

    public init(taskId: String, reason: String = "User requested cancellation from iOS") {
        self.taskId = taskId
        self.reason = reason
    }

    enum CodingKeys: String, CodingKey {
        case taskId = "task_id"
        case reason
    }
}

public struct TaskCancelResponse: Codable, Sendable {
    public let taskId: String
    public let success: Bool
    public let message: String
    public let timestamp: String

    enum CodingKeys: String, CodingKey {
        case taskId = "task_id"
        case success
        case message
        case timestamp
    }
}

public struct TaskRecord: Codable, Sendable, Identifiable {
    public var id: String { taskId }
    public let taskId: String
    public let requestId: String
    public let deviceId: String
    public let query: String
    public let status: TaskStatus
    public let createdAt: String
    public let updatedAt: String
    public let responseText: String?
    public let error: String?

    enum CodingKeys: String, CodingKey {
        case taskId = "task_id"
        case requestId = "request_id"
        case deviceId = "device_id"
        case query
        case status
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case responseText = "response_text"
        case error
    }
}

public struct EmergencyActionRequest: Codable, Sendable {
    public let action: String
    public let reason: String

    public init(action: String, reason: String = "User requested from iOS") {
        self.action = action
        self.reason = reason
    }
}

public struct EmergencyActionResponse: Codable, Sendable {
    public let action: String
    public let success: Bool
    public let message: String
    public let timestamp: String
}

public struct ProtocolErrorResponse: Codable, Sendable {
    public struct ErrorDetail: Codable, Sendable {
        public let code: String
        public let message: String
        public let details: [String: String]?
    }
    public let success: Bool
    public let protocolVersion: String?
    public let error: ErrorDetail

    enum CodingKeys: String, CodingKey {
        case success
        case protocolVersion = "protocol_version"
        case error
    }
}

public struct WebSocketEvent: Codable, Sendable {
    public let eventType: String
    public let timestamp: String?
    public let data: [String: String]?

    enum CodingKeys: String, CodingKey {
        case eventType = "event_type"
        case timestamp
        case data
    }
}

// =============================================================================
// Phase 05: Remote Computer Control Models
// =============================================================================

public struct WindowBounds: Codable, Sendable {
    public let x: Int
    public let y: Int
    public let width: Int
    public let height: Int
}

public struct WindowInfo: Codable, Sendable, Identifiable {
    public var id: Int { hwnd }
    public let hwnd: Int
    public let title: String
    public let processId: Int
    public let processName: String
    public let bounds: WindowBounds
    public let isVisible: Bool
    public let isMinimized: Bool
    public let isMaximized: Bool
    public let isForeground: Bool

    enum CodingKeys: String, CodingKey {
        case hwnd
        case title
        case processId = "process_id"
        case processName = "process_name"
        case bounds
        case isVisible = "is_visible"
        case isMinimized = "is_minimized"
        case isMaximized = "is_maximized"
        case isForeground = "is_foreground"
    }
}

public struct WindowFocusRequest: Codable, Sendable {
    public let hwnd: Int
    public init(hwnd: Int) { self.hwnd = hwnd }
}

public struct WindowCloseRequest: Codable, Sendable {
    public let hwnd: Int
    public init(hwnd: Int) { self.hwnd = hwnd }
}

public struct WindowBoundsRequest: Codable, Sendable {
    public let hwnd: Int
    public let x: Int
    public let y: Int
    public let width: Int
    public let height: Int

    public init(hwnd: Int, x: Int, y: Int, width: Int, height: Int) {
        self.hwnd = hwnd
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }
}

public struct AppInfo: Codable, Sendable, Identifiable {
    public var id: String { executablePath }
    public let name: String
    public let executablePath: String
    public let publisher: String?
    public let isRunning: Bool

    enum CodingKeys: String, CodingKey {
        case name
        case executablePath = "executable_path"
        case publisher
        case isRunning = "is_running"
    }
}

public struct AppLaunchRequest: Codable, Sendable {
    public let appNameOrPath: String
    public let arguments: [String]
    public let waitForWindow: Bool
    public let timeoutSeconds: Double

    public init(appNameOrPath: String, arguments: [String] = [], waitForWindow: Bool = true, timeoutSeconds: Double = 10.0) {
        self.appNameOrPath = appNameOrPath
        self.arguments = arguments
        self.waitForWindow = waitForWindow
        self.timeoutSeconds = timeoutSeconds
    }

    enum CodingKeys: String, CodingKey {
        case appNameOrPath = "app_name_or_path"
        case arguments
        case waitForWindow = "wait_for_window"
        case timeoutSeconds = "timeout_seconds"
    }
}

public struct AppLaunchResponse: Codable, Sendable {
    public let success: Bool
    public let pid: Int?
    public let hwnd: Int?
    public let windowDetected: Bool
    public let message: String?

    enum CodingKeys: String, CodingKey {
        case success
        case pid
        case hwnd
        case windowDetected = "window_detected"
        case message
    }
}

public struct ProcessInfo: Codable, Sendable, Identifiable {
    public var id: Int { pid }
    public let pid: Int
    public let name: String
    public let cpuPercent: Double
    public let memoryMb: Double
    public let status: String
    public let isProtected: Bool

    enum CodingKeys: String, CodingKey {
        case pid
        case name
        case cpuPercent = "cpu_percent"
        case memoryMb = "memory_mb"
        case status
        case isProtected = "is_protected"
    }
}

public struct ProcessStopRequest: Codable, Sendable {
    public let force: Bool
    public init(force: Bool = false) { self.force = force }
}

public struct ProcessStopResponse: Codable, Sendable {
    public let success: Bool
    public let pid: Int
    public let processName: String
    public let verifiedTerminated: Bool
    public let message: String?

    enum CodingKeys: String, CodingKey {
        case success
        case pid
        case processName = "process_name"
        case verifiedTerminated = "verified_terminated"
        case message
    }
}

public struct MouseMoveRequest: Codable, Sendable {
    public let x: Int
    public let y: Int
    public let relativeToHwnd: Int?

    public init(x: Int, y: Int, relativeToHwnd: Int? = nil) {
        self.x = x
        self.y = y
        self.relativeToHwnd = relativeToHwnd
    }

    enum CodingKeys: String, CodingKey {
        case x
        case y
        case relativeToHwnd = "relative_to_hwnd"
    }
}

public struct MouseClickRequest: Codable, Sendable {
    public let button: String
    public let count: Int
    public let x: Int?
    public let y: Int?
    public let relativeToHwnd: Int?

    public init(button: String = "left", count: Int = 1, x: Int? = nil, y: Int? = nil, relativeToHwnd: Int? = nil) {
        self.button = button
        self.count = count
        self.x = x
        self.y = y
        self.relativeToHwnd = relativeToHwnd
    }

    enum CodingKeys: String, CodingKey {
        case button
        case count
        case x
        case y
        case relativeToHwnd = "relative_to_hwnd"
    }
}

public struct MouseScrollRequest: Codable, Sendable {
    public let clicks: Int
    public let x: Int?
    public let y: Int?

    public init(clicks: Int, x: Int? = nil, y: Int? = nil) {
        self.clicks = clicks
        self.x = x
        self.y = y
    }
}

public struct KeyboardTypeRequest: Codable, Sendable {
    public let text: String
    public let targetHwnd: Int?

    public init(text: String, targetHwnd: Int? = nil) {
        self.text = text
        self.targetHwnd = targetHwnd
    }

    enum CodingKeys: String, CodingKey {
        case text
        case targetHwnd = "target_hwnd"
    }
}

public struct KeyPressRequest: Codable, Sendable {
    public let key: String
    public let targetHwnd: Int?

    public init(key: String, targetHwnd: Int? = nil) {
        self.key = key
        self.targetHwnd = targetHwnd
    }

    enum CodingKeys: String, CodingKey {
        case key
        case targetHwnd = "target_hwnd"
    }
}

public struct KeyComboRequest: Codable, Sendable {
    public let keys: [String]
    public let targetHwnd: Int?

    public init(keys: [String], targetHwnd: Int? = nil) {
        self.keys = keys
        self.targetHwnd = targetHwnd
    }

    enum CodingKeys: String, CodingKey {
        case keys
        case targetHwnd = "target_hwnd"
    }
}

public struct InputResponse: Codable, Sendable {
    public let success: Bool
    public let message: String?
}

