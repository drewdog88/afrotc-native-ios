import SwiftUI

/// Top-level switch: a brief loading state, then either the login screen or the
/// authenticated tab shell.
struct RootView: View {
    @EnvironmentObject private var session: Session

    var body: some View {
        switch session.phase {
        case .loading:
            ProgressView()
                .controlSize(.large)
        case .signedOut:
            LoginView()
        case .signedIn:
            MainTabView()
        }
    }
}

/// The authenticated shell — Dashboard, Recruits, Cadets.
struct MainTabView: View {
    @State private var selection = MainTabView.initialTab

    var body: some View {
        TabView(selection: $selection) {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "chart.bar.fill") }
                .tag("dashboard")
            RecruitsView()
                .tabItem { Label("Recruits", systemImage: "person.2.fill") }
                .tag("recruits")
            CadetsView()
                .tabItem { Label("Cadets", systemImage: "shield.lefthalf.filled") }
                .tag("cadets")
        }
    }

    /// Which tab to open on launch. Defaults to Dashboard; in DEBUG builds a
    /// `DET695_START_TAB` env var (dashboard|recruits|cadets) overrides it so
    /// each authenticated screen can be captured from the CLI.
    private static var initialTab: String {
        #if DEBUG
        return ProcessInfo.processInfo.environment["DET695_START_TAB"] ?? "dashboard"
        #else
        return "dashboard"
        #endif
    }
}
