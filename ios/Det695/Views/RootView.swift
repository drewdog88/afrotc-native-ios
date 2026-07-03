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

/// The authenticated shell. Five tabs — Dashboard, Recruits, Cadets, Pipeline,
/// and a More hub that holds Contacts, Events, Follow-ups, and Materials.
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
            NavigationStack { PipelineView() }
                .tabItem { Label("Pipeline", systemImage: "chart.line.uptrend.xyaxis") }
                .tag("pipeline")
            MoreView()
                .tabItem { Label("More", systemImage: "ellipsis.circle") }
                .tag("more")
        }
    }

    /// Which tab to open on launch. Defaults to Dashboard; in DEBUG builds a
    /// `DET695_START_TAB` env var (dashboard|recruits|cadets|pipeline|more)
    /// overrides it so each screen can be captured from the CLI.
    private static var initialTab: String {
        #if DEBUG
        return ProcessInfo.processInfo.environment["DET695_START_TAB"] ?? "dashboard"
        #else
        return "dashboard"
        #endif
    }
}

/// The overflow hub — a list that pushes the secondary screens onto one shared
/// NavigationStack. Each destination declares its own typed routes for detail.
struct MoreView: View {
    enum Destination: String, CaseIterable, Hashable {
        case contacts, events, followups, materials

        var title: String {
            switch self {
            case .contacts: "Contacts"
            case .events: "Events"
            case .followups: "Follow-ups"
            case .materials: "Materials"
            }
        }
        var icon: String {
            switch self {
            case .contacts: "building.columns"
            case .events: "calendar"
            case .followups: "checklist"
            case .materials: "folder"
            }
        }
    }

    @State private var path: [Destination] = MoreView.initialPath

    var body: some View {
        NavigationStack(path: $path) {
            List(Destination.allCases, id: \.self) { d in
                NavigationLink(value: d) {
                    Label(d.title, systemImage: d.icon)
                }
            }
            .navigationTitle("More")
            .navigationDestination(for: Destination.self) { dest in
                switch dest {
                case .contacts: ContactsView()
                case .events: EventsView()
                case .followups: FollowUpsView()
                case .materials: MaterialsView()
                }
            }
        }
    }

    /// In DEBUG, `DET695_MORE_DEST` (contacts|events|followups|materials) deep-links
    /// straight into a secondary screen so it can be captured from the CLI.
    private static var initialPath: [Destination] {
        #if DEBUG
        if let raw = ProcessInfo.processInfo.environment["DET695_MORE_DEST"],
           let d = Destination(rawValue: raw) {
            return [d]
        }
        #endif
        return []
    }
}
