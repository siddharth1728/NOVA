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

    public func sendAgentQuery(prompt: String) async throws -> RemoteQueryResponse {
        let reqPayload = RemoteQueryRequest(query: prompt)
        let bodyData = try JSONEncoder().encode(reqPayload)
        let req = try makeRequest(endpoint: "/api/v1/agent/query", method: "POST", body: bodyData)
        let (data, response) = try await session.data(for: req)
        try checkHttpResponse(response, data: data)
        return try JSONDecoder().decode(RemoteQueryResponse.self, from: data)
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
        } else if http.statusCode >= 400 {
            if let err = try? JSONDecoder().decode(ProtocolErrorResponse.self, from: data) {
                throw NovaClientError.serverError(err.error.message)
            }
            throw NovaClientError.serverError("HTTP \(http.statusCode)")
        }
    }
}
