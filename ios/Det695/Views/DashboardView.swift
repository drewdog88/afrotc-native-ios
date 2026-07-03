import SwiftUI

/// Detachment overview: headline stat tiles + "The Ascent" funnel, mirroring the
/// web dashboard.
struct DashboardView: View {
    @EnvironmentObject private var session: Session
    @State private var stats: DashboardStats?
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        NavigationStack {
            Group {
                if let stats {
                    content(stats)
                } else if loading {
                    ProgressView().controlSize(.large)
                } else if let error {
                    ContentUnavailableView("Couldn't load", systemImage: "exclamationmark.triangle",
                                           description: Text(error))
                } else {
                    Color.clear
                }
            }
            .navigationTitle("Dashboard")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Sign out") { Task { await session.logout() } }
                }
            }
            .task { await load() }
            .refreshable { await load() }
        }
    }

    @ViewBuilder
    private func content(_ s: DashboardStats) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    StatTile(label: "Recruits in pipeline", value: "\(s.totalRecruits)")
                    StatTile(label: "Active cadets", value: "\(s.totalCadets)")
                    StatTile(label: "Open follow-ups", value: "\(s.openFollowups)", accent: true)
                    StatTile(label: "Commissioned",
                             value: "\(s.recruitsByStage.first { $0.stageValue == .commissioned }?.count ?? 0)")
                }

                VStack(alignment: .leading, spacing: 12) {
                    Text("The Ascent")
                        .font(.title2.bold())
                    Text("Recruits by stage")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    FunnelChart(stages: s.recruitsByStage)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
            }
            .padding(16)
        }
        .background(Color(.systemGroupedBackground))
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            stats = try await APIClient.shared.dashboardStats()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct StatTile: View {
    let label: String
    let value: String
    var accent: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label.uppercased())
                .font(.caption2.weight(.semibold))
                .tracking(1)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(accent ? Theme.accent : Theme.ink)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

/// Horizontal funnel bars, apex first, width proportional to the largest stage.
private struct FunnelChart: View {
    let stages: [FunnelStageCount]

    private var ordered: [FunnelStageCount] {
        stages
            .filter { $0.stageValue != .declined }
            .sorted { $0.stageValue.funnelOrder < $1.stageValue.funnelOrder }
    }
    private var maxCount: Int { max(ordered.map(\.count).max() ?? 1, 1) }

    var body: some View {
        VStack(spacing: 8) {
            ForEach(ordered) { item in
                GeometryReader { geo in
                    let width = max(CGFloat(item.count) / CGFloat(maxCount) * geo.size.width, 44)
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(.tertiarySystemFill))
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Theme.stageColor(item.stageValue))
                            .frame(width: width)
                        HStack {
                            Text(item.stageValue.label)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.white)
                            Spacer()
                            Text("\(item.count)")
                                .font(.subheadline.weight(.bold))
                                .foregroundStyle(Theme.ink)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 2)
                                .background(.white, in: Capsule())
                        }
                        .padding(.horizontal, 12)
                    }
                }
                .frame(height: 40)
            }
        }
    }
}
