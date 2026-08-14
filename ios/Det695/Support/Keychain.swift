import Foundation
import Security

private let kcLog = DebugLog(category: "keychain")

/// Minimal Keychain-backed string store for the JWT access/refresh pair.
/// Values live in the login keychain keyed by a service + account string.
enum Keychain {
    private static let service = "com.det695.recruiting.tokens"

    static func set(_ value: String?, for account: String) {
        // Delete any existing item first, then insert (simplest correct upsert).
        let base: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(base as CFDictionary)

        guard let value, let data = value.data(using: .utf8) else { return }
        var add = base
        add[kSecValueData as String] = data
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        let status = SecItemAdd(add as CFDictionary, nil)
        if status != errSecSuccess {
            kcLog.error("SecItemAdd(\(account)) failed: OSStatus=\(status) (\(SecCopyErrorMessageString(status, nil) as String? ?? "?"))")
        } else {
            kcLog.notice("SecItemAdd(\(account)) ok, \(data.count) bytes")
        }
    }

    static func get(_ account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else {
            kcLog.error("SecItemCopyMatching(\(account)) miss: OSStatus=\(status) (\(SecCopyErrorMessageString(status, nil) as String? ?? "?"))")
            return nil
        }
        return String(data: data, encoding: .utf8)
    }
}
