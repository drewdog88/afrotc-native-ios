import SwiftUI

/// Shared navigation state so one screen can drive another — e.g. a Dashboard
/// stat tile jumps to its tab, and the More hub's deep path is hoisted here so
/// the Dashboard can open Follow-ups directly. Injected into the environment by
/// `MainTabView`.
@MainActor
final class AppRouter: ObservableObject {
    @Published var tab: String
    /// Type-erased so the shared More stack can push heterogeneous routes —
    /// `Destination` (the hub rows) plus each secondary screen's own route
    /// (`EventRoute`, `ContactRoute`, `RecruitRoute`). A homogeneous `[Destination]`
    /// binding would silently drop links of any other type, breaking their detail
    /// navigation.
    @Published var morePath: NavigationPath

    /// A one-shot filter handed to a list when a summary drills into it — the
    /// list applies it once on receipt, then clears it. Mirrors the web
    /// `/recruits?stage=` / `/cadets?status=` deep links.
    @Published var pendingRecruitStage: RecruitStage?
    @Published var pendingCadetStatus: String?

    init(tab: String = "dashboard", morePath: NavigationPath = NavigationPath()) {
        self.tab = tab
        self.morePath = morePath
    }

    /// Jump to a top-level tab.
    func select(_ tab: String) { self.tab = tab }

    /// Open the Recruits tab, optionally pre-filtered to a stage.
    func openRecruits(stage: RecruitStage? = nil) {
        pendingRecruitStage = stage
        tab = "recruits"
    }

    /// Open the Cadets tab, optionally pre-filtered to a status.
    func openCadets(status: String? = nil) {
        pendingCadetStatus = status
        tab = "cadets"
    }

    /// Open a screen that lives under the More hub (e.g. Follow-ups).
    func openMore(_ dest: MoreView.Destination) {
        var path = NavigationPath()
        path.append(dest)
        morePath = path
        tab = "more"
    }
}

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
    @StateObject private var router = AppRouter(tab: MainTabView.initialTab,
                                               morePath: MoreView.initialPath)

    var body: some View {
        TabView(selection: $router.tab) {
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
        .environmentObject(router)
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
        case contacts, events, followups, materials, profile, admin

        var title: String {
            switch self {
            case .contacts: "Contacts"
            case .events: "Events"
            case .followups: "Follow-ups"
            case .materials: "Materials"
            case .profile: "Profile & Security"
            case .admin: "Admin"
            }
        }
        var icon: String {
            switch self {
            case .contacts: "building.columns"
            case .events: "calendar"
            case .followups: "checklist"
            case .materials: "folder"
            case .profile: "person.crop.circle"
            case .admin: "person.2.badge.gearshape"
            }
        }
        /// `.admin` is only surfaced to detachment admins; everything else is
        /// visible to any signed-in user.
        var adminOnly: Bool { self == .admin }
    }

    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var session: Session

    /// Hub rows the current user may see — `.admin` is dropped for non-admins.
    private var destinations: [Destination] {
        let isAdmin = session.user?.isAdmin == true
        return Destination.allCases.filter { isAdmin || !$0.adminOnly }
    }

    var body: some View {
        NavigationStack(path: $router.morePath) {
            List(destinations, id: \.self) { d in
                NavigationLink(value: d) {
                    Label(d.title, systemImage: d.icon)
                }
            }
            .navigationTitle("More")
            .navigationBarTitleDisplayMode(.inline)
            .det695BrandBar()
            .navigationDestination(for: Destination.self) { dest in
                switch dest {
                case .contacts: ContactsView()
                case .events: EventsView()
                case .followups: FollowUpsView()
                case .materials: MaterialsView()
                case .profile: ProfileView()
                case .admin: AdminView()
                }
            }
        }
    }

    /// In DEBUG, `DET695_MORE_DEST` (contacts|events|followups|materials) deep-links
    /// straight into a secondary screen so it can be captured from the CLI.
    static var initialPath: NavigationPath {
        #if DEBUG
        if let raw = ProcessInfo.processInfo.environment["DET695_MORE_DEST"],
           let d = Destination(rawValue: raw) {
            var path = NavigationPath()
            path.append(d)
            return path
        }
        #endif
        return NavigationPath()
    }
}
