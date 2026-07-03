import SwiftUI

/// Recruiter task queue grouped by urgency (Overdue / Today / Upcoming) with a
/// Done archive, mirroring the web Follow-ups page. Tapping the checkbox marks a
/// task complete. Recruit names are resolved from a lightweight recruits fetch.
struct FollowUpsView: View {
    @State private var followups: [FollowUpOut] = []
    @State private var recruitNames: [Int: String] = [:]
    @State private var error: String?
    @State private var loading = false
    @State private var completing: Set<Int> = []

    var body: some View {
        List {
            if let error {
                Text(error).foregroundStyle(Theme.danger)
            }
            group("Overdue", overdue, tint: Theme.danger)
            group("Today", today, tint: Theme.accent)
            group("Upcoming", upcoming, tint: Theme.muted)
            if !done.isEmpty {
                Section("Done") {
                    ForEach(done) { f in row(f) }
                }
            }
            if followups.isEmpty && !loading && error == nil {
                ContentUnavailableView("No follow-ups", systemImage: "checklist")
            }
        }
        .listStyle(.insetGrouped)
        .overlay { if loading && followups.isEmpty { ProgressView() } }
        .navigationTitle("Follow-ups")
        .navigationDestination(for: RecruitRoute.self) { RecruitDetailView(recruitId: $0.id) }
        .task { await load() }
        .refreshable { await load() }
    }

    @ViewBuilder
    private func group(_ title: String, _ items: [FollowUpOut], tint: Color) -> some View {
        if !items.isEmpty {
            Section {
                ForEach(items) { f in row(f) }
            } header: {
                HStack {
                    Text(title)
                    Spacer()
                    Text("\(items.count)").foregroundStyle(tint)
                }
            }
        }
    }

    @ViewBuilder
    private func row(_ f: FollowUpOut) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Button {
                Task { await complete(f) }
            } label: {
                Image(systemName: f.isDone ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundStyle(f.isDone ? Theme.ok : Theme.muted)
            }
            .buttonStyle(.plain)
            .disabled(f.isDone || completing.contains(f.id))

            VStack(alignment: .leading, spacing: 3) {
                Text(f.note)
                    .strikethrough(f.isDone)
                    .foregroundStyle(f.isDone ? .secondary : .primary)
                Text(dueLabel(f)).font(.caption).foregroundStyle(.secondary)
                if let rid = f.recruitId {
                    NavigationLink(value: RecruitRoute(id: rid)) {
                        Text(recruitNames[rid] ?? "Recruit #\(rid)")
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 8).padding(.vertical, 2)
                            .background(Theme.ink.opacity(0.08), in: Capsule())
                            .foregroundStyle(Theme.ink)
                    }
                    .buttonStyle(.plain)
                }
            }
            Spacer()
        }
        .padding(.vertical, 2)
    }

    private func dueLabel(_ f: FollowUpOut) -> String {
        if f.isDone { return "Completed \(DateDisplay.mediumDate(f.completedAt))" }
        return "Due \(DateDisplay.mediumDateTime(f.dueDate))"
    }

    // MARK: - Grouping

    private var startOfToday: Date { Calendar.current.startOfDay(for: .now) }
    private var startOfTomorrow: Date { Calendar.current.date(byAdding: .day, value: 1, to: startOfToday)! }

    private var open: [FollowUpOut] {
        followups.filter { !$0.isDone }.sorted { $0.dueDate < $1.dueDate }
    }
    private var overdue: [FollowUpOut] {
        open.filter { (DateDisplay.parseDateTime($0.dueDate) ?? .distantFuture) < startOfToday }
    }
    private var today: [FollowUpOut] {
        open.filter {
            let d = DateDisplay.parseDateTime($0.dueDate) ?? .distantFuture
            return d >= startOfToday && d < startOfTomorrow
        }
    }
    private var upcoming: [FollowUpOut] {
        open.filter { (DateDisplay.parseDateTime($0.dueDate) ?? .distantPast) >= startOfTomorrow }
    }
    private var done: [FollowUpOut] {
        followups.filter { $0.isDone }
            .sorted { ($0.completedAt ?? $0.dueDate) > ($1.completedAt ?? $1.dueDate) }
    }

    // MARK: - Actions

    private func complete(_ f: FollowUpOut) async {
        completing.insert(f.id)
        defer { completing.remove(f.id) }
        do {
            let updated = try await APIClient.shared.completeFollowup(id: f.id)
            if let i = followups.firstIndex(where: { $0.id == f.id }) { followups[i] = updated }
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            async let fus = APIClient.shared.followups().items
            async let recs = APIClient.shared.recruits().items
            followups = try await fus
            recruitNames = Dictionary(uniqueKeysWithValues: try await recs.map { ($0.id, $0.fullName) })
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
