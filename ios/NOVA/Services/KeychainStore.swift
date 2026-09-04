//
//  KeychainStore.swift
//  NOVA iOS Control Center
//
//  Secure credential and host endpoint persistence.
//

import Foundation
import Security

public final class KeychainStore: @unchecked Sendable {
    public static let shared = KeychainStore()

    private let service = "com.antigravity.nova.ios"
    private let tokenAccount = "authToken"
    private let deviceIdAccount = "deviceId"
    private let hostUrlAccount = "hostBaseUrl"

    private init() {}

    public var hostBaseUrl: String {
        get {
            UserDefaults.standard.string(forKey: "nova_host_url") ?? "http://192.168.1.100:8000"
        }
        set {
            UserDefaults.standard.set(newValue, forKey: "nova_host_url")
        }
    }

    public var deviceId: String {
        get {
            if let existing = UserDefaults.standard.string(forKey: "nova_device_id") {
                return existing
            }
            let newId = "ios-" + UUID().uuidString.lowercased()
            UserDefaults.standard.set(newId, forKey: "nova_device_id")
            return newId
        }
    }

    public var authToken: String? {
        get {
            readKeychain(account: tokenAccount)
        }
        set {
            if let token = newValue {
                saveKeychain(account: tokenAccount, value: token)
            } else {
                deleteKeychain(account: tokenAccount)
            }
        }
    }

    public var isPaired: Bool {
        return authToken != nil
    }

    public func clearAll() {
        deleteKeychain(account: tokenAccount)
        UserDefaults.standard.removeObject(forKey: "nova_device_id")
    }

    // MARK: - Private Keychain Helpers

    private func saveKeychain(account: String, value: String) {
        guard let data = value.data(using: .utf8) else { return }
        deleteKeychain(account: account)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    private func readKeychain(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    private func deleteKeychain(account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }
}
