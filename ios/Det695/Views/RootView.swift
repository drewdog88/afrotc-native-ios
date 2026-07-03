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
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "chart.bar.fill") }
            RecruitsView()
                .tabItem { Label("Recruits", systemImage: "person.2.fill") }
            CadetsView()
                .tabItem { Label("Cadets", systemImage: "shield.lefthalf.filled") }
        }
    }
}
