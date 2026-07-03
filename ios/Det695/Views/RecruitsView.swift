import SwiftUI

/// Recruits list with search + stage filter, mirroring the web Recruits page.
struct RecruitsView: View {
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
                    RecruitRow(recruit: r)
                }
                if recruits.isEmpty && !loading && error == nil {
                    ContentUnavailableView("No recruits", systemImage: "person.2")
                }
            }
            .listStyle(.plain)
            .overlay { if loading && recruits.isEmpty { ProgressView() } }
            .navigationTitle("Recruits")
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
