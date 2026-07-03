import SwiftUI

/// Typed navigation route to a cadet detail, distinct from other Int routes.
struct CadetRoute: Hashable { let id: Int }

/// Cadets directory with search + status filter (active / inactive / graduated),
/// mirroring the web Cadets page.
struct CadetsView: View {
    private static let statuses = ["active", "inactive", "graduated"]

    @EnvironmentObject private var router: AppRouter

    @State private var cadets: [CadetOut] = []
    @State private var search = ""
    @State private var status: String?
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        NavigationStack {
            List {
                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                }
                ForEach(cadets) { c in
                    NavigationLink(value: CadetRoute(id: c.id)) { CadetRow(cadet: c) }
                }
                if cadets.isEmpty && !loading && error == nil {
                    ContentUnavailableView("No cadets", systemImage: "shield")
                }
            }
            .listStyle(.plain)
            .overlay { if loading && cadets.isEmpty { ProgressView() } }
            .navigationTitle("Cadets")
            .navigationDestination(for: CadetRoute.self) { CadetDetailView(cadetId: $0.id) }
            .searchable(text: $search, prompt: "Search cadets")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("All statuses") { status = nil }
                        Divider()
                        ForEach(Self.statuses, id: \.self) { s in
                            Button(s.capitalized) { status = s }
                        }
                    } label: {
                        Label(status?.capitalized ?? "All", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
            .task(id: filterKey) { await load() }
            .refreshable { await load() }
            .onAppear { applyPendingStatus() }
            .onChange(of: router.pendingCadetStatus) { oldValue, newValue in
                applyPendingStatus()
            }
        }
    }

    private func applyPendingStatus() {
        guard let pendingStatus = router.pendingCadetStatus else { return }
        status = pendingStatus
        router.pendingCadetStatus = nil
    }

    private var filterKey: String { "\(search)|\(status ?? "")" }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            cadets = try await APIClient.shared.cadets(search: search, status: status).items
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct CadetRow: View {
    let cadet: CadetOut

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(Theme.cadetStatusColor(cadet.status))
                .frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text(cadet.fullName).font(.body.weight(.semibold))
                Text("\(cadet.cadetRank) · \(cadet.major)")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Text(cadet.statusLabel)
                .font(.caption2.weight(.semibold))
                .foregroundStyle(Theme.cadetStatusColor(cadet.status))
        }
        .padding(.vertical, 4)
    }
}

/// Read-only cadet detail, fetched fresh by id. Mirrors the web cadet detail:
/// profile fields plus unenrollment info when the cadet is inactive.
struct CadetDetailView: View {
    let cadetId: Int
    @State private var cadet: CadetOut?
    @State private var error: String?

    var body: some View {
        Group {
            if let c = cadet {
                Form {
                    Section {
                        LabeledRow("Name", c.fullName)
                        HStack {
                            Text("Status").foregroundStyle(.secondary)
                            Spacer()
                            Text(c.statusLabel)
                                .foregroundStyle(Theme.cadetStatusColor(c.status))
                        }
                        LabeledRow("Rank", c.cadetRank)
                        LabeledRow("Major", c.major)
                        LabeledRow("Graduation year", String(c.graduationYear))
                        if let g = c.gpa { LabeledRow("GPA", String(format: "%.2f", g)) }
                        if let h = c.hometown, !h.isEmpty { LabeledRow("Hometown", h) }
                    }
                    Section("Reach") {
                        LinkRow(label: "Email", value: c.email, url: URL(string: "mailto:\(c.email)"))
                        if let p = c.phone, !p.isEmpty {
                            LinkRow(label: "Phone", value: p,
                                    url: URL(string: "tel:\(p.filter { $0.isNumber || $0 == "+" })"))
                        }
                    }
                    if let o = c.officerInterest, !o.isEmpty {
                        Section("Officer interest") { Text(o) }
                    }
                    if c.status.lowercased() == "inactive" {
                        Section("Unenrollment") {
                            if let r = c.unenrollmentReason, !r.isEmpty { LabeledRow("Reason", r) }
                            if let d = c.unenrollmentDate, !d.isEmpty {
                                LabeledRow("Date", DateDisplay.mediumDate(d))
                            }
                        }
                    }
                }
            } else if let error {
                ContentUnavailableView("Couldn't load", systemImage: "exclamationmark.triangle",
                                       description: Text(error))
            } else {
                ProgressView()
            }
        }
        .navigationTitle(cadet?.fullName ?? "Cadet")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        do { cadet = try await APIClient.shared.cadet(id: cadetId) }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }
}
