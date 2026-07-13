import SwiftUI
import Charts

/// Detachment overview: headline stat tiles + "The Ascent" funnel + a new-recruits
/// trend chart, mirroring the web dashboard.
struct DashboardView: View {
    @EnvironmentObject private var session: Session
    @EnvironmentObject private var router: AppRouter
    @State private var stats: DashboardStats?
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        NavigationStack {
            Group {
                if let stats {
                    content(stats)
                } else if loading {
                    skeleton
                } else if let error {
                    ContentUnavailableView("Couldn't load", systemImage: "exclamationmark.triangle",
                                           description: Text(error))
                } else {
                    Color.clear
                }
            }
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.inline)
            .det695BrandBar()
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
        let commissioned = s.recruitsByStage.first { $0.stageValue == .commissioned }?.count ?? 0
        let commissionRate = s.totalRecruits > 0
            ? Int((Double(commissioned) / Double(s.totalRecruits) * 100).rounded()) : 0

        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Detachment overview").font(.title2.bold())
                    Text("Live recruiting pipeline and momentum across Det 695.")
                        .font(.subheadline).foregroundStyle(.secondary)
                }

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    Button { router.openRecruits() } label: {
                        StatTile(label: "Recruits in pipeline", value: "\(s.totalRecruits)",
                                 note: "across all stages")
                    }
                    .buttonStyle(.plain)

                    Button { router.openRecruits(stage: .commissioned) } label: {
                        StatTile(label: "Commissioned", value: "\(commissioned)",
                                 note: "\(commissionRate)% of pipeline")
                    }
                    .buttonStyle(.plain)

                    Button { router.openCadets(status: "active") } label: {
                        StatTile(label: "Active cadets", value: "\(s.totalCadets)",
                                 note: "on the roster")
                    }
                    .buttonStyle(.plain)

                    Button { router.openMore(.followups) } label: {
                        StatTile(label: "Open follow-ups", value: "\(s.openFollowups)",
                                 note: s.openFollowups > 0 ? "needs attention" : "all clear",
                                 accent: true)
                    }
                    .buttonStyle(.plain)
                }

                panel(title: "The Ascent", note: "Recruits by stage · conversion from the stage below") {
                    FunnelChart(stages: s.recruitsByStage, onSelect: { router.openRecruits(stage: $0) })
                }

                panel(title: "New recruits", note: "Entering the pipeline · by week") {
                    TrendChart(points: s.recentTrend)
                }
            }
            .padding(16)
            .padding(.bottom, 24) // clear the floating tab bar
        }
        .background(Color(.systemGroupedBackground))
    }

    @ViewBuilder
    private func panel<Content: View>(title: String, note: String,
                                      @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.title3.bold())
                Text(note).font(.caption).foregroundStyle(.secondary)
            }
            content()
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }

    /// Shimmering placeholders while the first load is in flight.
    private var skeleton: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    ForEach(0..<4, id: \.self) { _ in
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color(.secondarySystemGroupedBackground))
                            .frame(height: 104)
                    }
                }
                ForEach(0..<2, id: \.self) { _ in
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color(.secondarySystemGroupedBackground))
                        .frame(height: 240)
                }
            }
            .padding(16)
            .redacted(reason: .placeholder)
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
    var note: String? = nil
    var accent: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Reserve two lines so single- and double-line labels leave the value
            // on the same baseline across a row.
            Text(label.uppercased())
                .font(.caption2.weight(.semibold))
                .tracking(1)
                .foregroundStyle(.secondary)
                .lineLimit(2, reservesSpace: true)
            Text(value)
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(accent ? Theme.accent : Theme.ink)
            if let note {
                Text(note)
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

/// Single-series area chart for new recruits over time, mirroring the web TrendArea.
private struct TrendChart: View {
    let points: [TrendPoint]

    /// "2026-W27" -> "W27"
    private func weekLabel(_ period: String) -> String {
        if let r = period.range(of: #"W\d+$"#, options: .regularExpression) {
            return String(period[r])
        }
        return period
    }

    var body: some View {
        if points.isEmpty {
            Text("No stage activity recorded yet.")
                .font(.footnote).foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, minHeight: 160)
        } else {
            Chart(points) { p in
                AreaMark(
                    x: .value("Week", weekLabel(p.period)),
                    y: .value("Recruits", p.count)
                )
                .foregroundStyle(
                    .linearGradient(colors: [Theme.accent.opacity(0.28), Theme.accent.opacity(0.02)],
                                    startPoint: .top, endPoint: .bottom)
                )
                .interpolationMethod(.catmullRom)

                LineMark(
                    x: .value("Week", weekLabel(p.period)),
                    y: .value("Recruits", p.count)
                )
                .foregroundStyle(Theme.accent)
                .interpolationMethod(.catmullRom)
                .symbol(.circle)
            }
            .frame(height: 200)
        }
    }
}

/// Horizontal funnel bars, apex first, width proportional to the largest stage,
/// each labeled with its stage blurb and stage-to-stage conversion.
private struct FunnelChart: View {
    let stages: [FunnelStageCount]
    let onSelect: (RecruitStage) -> Void

    private var ordered: [FunnelStageCount] {
        stages
            .filter { $0.stageValue != .declined }
            .sorted { $0.stageValue.funnelOrder < $1.stageValue.funnelOrder }
    }
    private var maxCount: Int { max(ordered.map(\.count).max() ?? 1, 1) }

    /// Conversion vs the stage directly below (next lower altitude), or nil for
    /// the base of the funnel.
    private func conversion(at index: Int) -> Int? {
        guard index + 1 < ordered.count else { return nil }
        let below = ordered[index + 1].count
        guard below > 0 else { return nil }
        return Int((Double(ordered[index].count) / Double(below) * 100).rounded())
    }

    var body: some View {
        VStack(spacing: 8) {
            ForEach(Array(ordered.enumerated()), id: \.element.id) { index, item in
                Button {
                    onSelect(item.stageValue)
                } label: {
                    band(item: item, conversion: conversion(at: index))
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func band(item: FunnelStageCount, conversion: Int?) -> some View {
        GeometryReader { geo in
            let width = max(CGFloat(item.count) / CGFloat(maxCount) * geo.size.width, 132)
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(.tertiarySystemFill))
                RoundedRectangle(cornerRadius: 8)
                    .fill(Theme.stageColor(item.stageValue))
                    .frame(width: width)
                HStack {
                    VStack(alignment: .leading, spacing: 1) {
                        Text(item.stageValue.label)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.white)
                        Text(item.stageValue.blurb)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.85))
                            .lineLimit(1)
                    }
                    Spacer()
                    HStack(spacing: 6) {
                        Text("\(item.count)")
                            .font(.subheadline.weight(.bold))
                            .foregroundStyle(Theme.ink)
                            .padding(.horizontal, 8).padding(.vertical, 2)
                            .background(.white, in: Capsule())
                        Text(conversion.map { "\($0)%" } ?? "—")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.white)
                            .frame(width: 40, alignment: .trailing)
                    }
                }
                .padding(.horizontal, 12)
            }
        }
        .frame(height: 52)
    }
}
