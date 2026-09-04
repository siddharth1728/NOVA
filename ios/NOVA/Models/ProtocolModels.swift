//
//  ProtocolModels.swift
//  NOVA iOS Control Center
//
//  Shared typed data models corresponding to NOVA Remote Protocol v1.
//

import Foundation

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

public struct PairingRequest: Codable, Sendable {
    public let pairingCode: String
    public let deviceId: String
    public let deviceName: String
    public let platform: String

    public init(pairingCode: String, deviceId: String, deviceName: String, platform: String = "iOS") {
        self.pairingCode = pairingCode
        self.deviceId = deviceId
        self.deviceName = deviceName
        self.platform = platform
    }

    enum CodingKeys: String, CodingKey {
        case pairingCode = "pairing_code"
        case deviceId = "device_id"
        case deviceName = "device_name"
        case platform
    }
}

public struct PairingResponse: Codable, Sendable {
    public let token: String
    public let deviceId: String
    public let hostName: String
    public let serverVersion: String
    public let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case token
        case deviceId = "device_id"
        case hostName = "host_name"
        case serverVersion = "server_version"
        case expiresAt = "expires_at"
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
    public let system: SystemMetrics
    public let agent: AgentStatus
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
    public let available: bool
    public let riskLevel: String
    public let description: String

    enum CodingKeys: String, CodingKey {
        case name
        case available
        case riskLevel = "risk_level"
        case description
    }
}

public struct CapabilitiesMatrix: Codable, Sendable {
    public let version: String
    public let hostPlatform: String
    public let capabilities: [CapabilityInfo]

    enum CodingKeys: String, CodingKey {
        case version
        case hostPlatform = "host_platform"
        case capabilities
    }
}

public struct RemoteQueryRequest: Codable, Sendable {
    public let query: String
    public let requireApproval: Bool
    public let maxSteps: Int

    public init(query: String, requireApproval: Bool = false, maxSteps: Int = 10) {
        self.query = query
        self.requireApproval = requireApproval
        self.maxSteps = maxSteps
    }

    enum CodingKeys: String, CodingKey {
        case query
        case requireApproval = "require_approval"
        case maxSteps = "max_steps"
    }
}

public struct RemoteQueryResponse: Codable, Sendable {
    public let sessionId: String
    public let query: String
    public let status: String
    public let responseText: String
    public let toolCallsCount: Int
    public let stepsExecuted: Int
    public let verificationPassed: Bool
    public let planId: String?

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case query
        case status
        case responseText = "response_text"
        case toolCallsCount = "tool_calls_count"
        case stepsExecuted = "steps_executed"
        case verificationPassed = "verification_passed"
        case planId = "plan_id"
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
    }
    public let success: Bool
    public let error: ErrorDetail
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
