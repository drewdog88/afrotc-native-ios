import SwiftUI

/// Typed navigation route to a recruit detail, distinct from other Int routes.
struct RecruitRoute: Hashable { let id: Int }

/// Recruits list with search + stage filter, mirroring the web Recruits page.
struct RecruitsView: View {
    @EnvironmentObject private var router: AppRouter
    @State private var recruits: [RecruitOut] = []
    @State private var search = ""
    @State private var stage: RecruitStage?
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        NavigationStack {
            List {
                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                }
                ForEach(recruits) { r in
                    NavigationLink(value: RecruitRoute(id: r.id)) { RecruitRow(recruit: r) }
                }
                if recruits.isEmpty && !loading && error == nil {
                    ContentUnavailableView("No recruits", systemImage: "person.2")
                }
            }
            .listStyle(.plain)
            .overlay { if loading && recruits.isEmpty { ProgressView() } }
            .navigationTitle("Recruits")
            .navigationDestination(for: RecruitRoute.self) { RecruitDetailView(recruitId: $0.id) }
            .searchable(text: $search, prompt: "Search recruits")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("All stages") { stage = nil }
                        Divider()
                        ForEach(RecruitStage.allCases) { s in
                            Button(s.label) { stage = s }
                        }
                    } label: {
                        Label(stage?.label ?? "All", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
            .task(id: filterKey) { await load() }
            .refreshable { await load() }
            .onAppear {
                if let pendingStage = router.pendingRecruitStage {
                    stage = pendingStage
                    router.pendingRecruitStage = nil
                }
            }
            .onChange(of: router.pendingRecruitStage) { oldValue, newValue in
                if let newStage = newValue {
                    stage = newStage
                    router.pendingRecruitStage = nil
                }
            }
        }
    }

    private var filterKey: String { "\(search)|\(stage?.rawValue ?? "")" }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            recruits = try await APIClient.shared.recruits(search: search, stage: stage).items
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct RecruitRow: View {
    let recruit: RecruitOut

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(recruit.fullName).font(.body.weight(.semibold))
                Text(recruit.currentSchool).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            StageBadge(stage: recruit.stageValue)
        }
        .padding(.vertical, 4)
    }
}

struct StageBadge: View {
    let stage: RecruitStage
    var body: some View {
        Text(stage.label)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(Theme.stageColor(stage).opacity(0.18), in: Capsule())
            .foregroundStyle(Theme.stageColor(stage))
    }
}

/// Read-only recruit detail: profile fields plus the stage-transition history,
/// mirroring the web RecruitDetail page. Both are fetched fresh by id.
struct RecruitDetailView: View {
    let recruitId: Int
    @State private var recruit: RecruitOut?
    @State private var history: [StageEvent] = []
    @State private var error: String?

    var body: some View {
        Group {
            if let r = recruit {
                Form {
                    Section {
                        LabeledRow("Name", r.fullName)
                        HStack {
                            Text("Stage").foregroundStyle(.secondary)
                            Spacer()
                            StageBadge(stage: r.stageValue)
                        }
                        LabeledRow("School", r.currentSchool)
                        LabeledRow("Type", schoolTypeLabel(r.schoolType))
                        if let m = r.major, !m.isEmpty { LabeledRow("Major", m) }
                        if let g = r.gpa { LabeledRow("GPA", String(format: "%.2f", g)) }
                    }
                    Section("Reach") {
                        if let e = r.email, !e.isEmpty {
                            LinkRow(label: "Email", value: e, url: URL(string: "mailto:\(e)"))
                        }
                        if let p = r.phone, !p.isEmpty {
                            LinkRow(label: "Phone", value: p,
                                    url: URL(string: "tel:\(p.filter { $0.isNumber || $0 == "+" })"))
                        }
                    }
                    if let i = r.interests, !i.isEmpty {
                        Section("Interests") { Text(i) }
                    }
                    if let n = r.notes, !n.isEmpty {
                        Section("Notes") { Text(n) }
                    }
                    Section("Stage history") {
                        if history.isEmpty {
                            Text("No transitions recorded").foregroundStyle(.secondary)
                        } else {
                            ForEach(history) { StageEventRow(event: $0) }
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
        .navigationTitle(recruit?.fullName ?? "Recruit")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func schoolTypeLabel(_ raw: String) -> String {
        switch raw.lowercased() {
        case "high_school": return "High school"
        case "college", "university": return "College"
        default: return raw.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private func load() async {
        do {
            async let r = APIClient.shared.recruit(id: recruitId)
            async let h = APIClient.shared.recruitStageHistory(id: recruitId)
            recruit = try await r
            history = (try? await h) ?? []
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// One stage transition: "From → To" with the date and optional note.
private struct StageEventRow: View {
    let event: StageEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                if let from = event.fromStageValue {
                    StageBadge(stage: from)
                    Image(systemName: "arrow.right").font(.caption2).foregroundStyle(.secondary)
                }
                StageBadge(stage: event.toStageValue)
                Spacer()
                Text(DateDisplay.mediumDate(event.changedAt))
                    .font(.caption).foregroundStyle(.secondary)
            }
            if let n = event.note, !n.isEmpty {
                Text(n).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}
