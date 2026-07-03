import SwiftUI

/// App entry point. Owns the shared `Session` and hands it to the view tree,
/// which decides between the login screen and the authenticated tab shell.
@main
struct Det695App: App {
    @StateObject private var session = Session()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .tint(Theme.accent)
        }
    }
}
