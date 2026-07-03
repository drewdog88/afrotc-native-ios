import SwiftUI
import Charts

/// Recruitment analytics, mirroring the web Pipeline page: a cumulative
/// reach-by-stage trend chart (week/month) plus a current funnel + stage
/// conversion table.
struct PipelineView: View {
    @State private var funnel: FunnelResponse?
    @State private var trends: TrendsResponse?
    @State private var interval = "week"
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                }

                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Cumulative reach").font(.title3.bold())
                        Spacer()
                        Picker("Interval", selection: $interval) {
                            Text("Week").tag("week")
                            Text("Month").tag("month")
                        }
                        .pickerStyle(.segmented)
                        .frame(width: 160)
                    }
                    Text("Recruits reaching each stage over time")
                        .font(.subheadline).foregroundStyle(.secondary)
                    TrendChart(points: cumulativePoints)
                        .frame(height: 240)
                }
                .cardBackground()

                VStack(alignment: .leading, spacing: 12) {
                    Text("Stage conversion").font(.title3.bold())
                    ConversionTable(stages: funnel?.stages ?? [], total: funnel?.total ?? 0)
                }
                .cardBackground()
            }
            .padding(16)
        }
        .background(Color(.systemGroupedBackground))
        .overlay { if loading && funnel == nil { ProgressView().controlSize(.large) } }
        .navigationTitle("Pipeline")
        .navigationBarTitleDisplayMode(.inline)
        .det695BrandBar()
        .task(id: interval) { await load() }
        .refreshable { await load() }
    }

    /// One point per (stage, period) carrying the running cumulative total the web
    /// chart plots — recruits that have reached each stage by that period.
    private var cumulativePoints: [CumulativePoint] {
        guard let trends else { return [] }
        var out: [CumulativePoint] = []
        for series in trends.series {
            var running = 0
            for p in series.points.sorted(by: { $0.period < $1.period }) {
                running += p.count
                out.append(CumulativePoint(stage: series.stageValue, period: p.period, total: running))
            }
        }
        return out
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            async let f = APIClient.shared.analyticsFunnel()
            async let t = APIClient.shared.analyticsTrends(interval: interval)
            funnel = try await f
            trends = try await t
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct CumulativePoint: Identifiable {
    let stage: RecruitStage
    let period: String
    let total: Int
    var id: String { "\(stage.rawValue)-\(period)" }
}

/// Multi-series line chart, one line per stage in its brand color.
private struct TrendChart: View {
    let points: [CumulativePoint]

    var body: some View {
        if points.isEmpty {
            ContentUnavailableView("No trend data", systemImage: "chart.xyaxis.line")
                .frame(maxWidth: .infinity)
        } else {
            Chart(points) { p in
                LineMark(
                    x: .value("Period", p.period),
                    y: .value("Reached", p.total)
                )
                .foregroundStyle(by: .value("Stage", p.stage.label))
                .symbol(by: .value("Stage", p.stage.label))
            }
            .chartForegroundStyleScale(domain: stageDomain, range: stageRange)
            .chartLegend(position: .bottom, spacing: 8)
            .chartXAxis { AxisMarks(values: .automatic(desiredCount: 4)) }
        }
    }

    /// Stable stage→color mapping so a line's color follows its stage, not its
    /// rank in the data (matches the web palette).
    private var presentStages: [RecruitStage] {
        var seen: [RecruitStage] = []
        for p in points where !seen.contains(p.stage) { seen.append(p.stage) }
        return seen.sorted { $0.funnelOrder > $1.funnelOrder }
    }
    private var stageDomain: [String] { presentStages.map(\.label) }
    private var stageRange: [Color] { presentStages.map { Theme.stageColor($0) } }
}

/// Stage / count / conversion-to-next table.
private struct ConversionTable: View {
    let stages: [FunnelStageCount]
    let total: Int

    private var ordered: [FunnelStageCount] {
        stages.filter { $0.stageValue != .declined }
            .sorted { $0.stageValue.funnelOrder > $1.stageValue.funnelOrder } // lead → commissioned
    }

    var body: some View {
        if total == 0 {
            ContentUnavailableView("No recruits yet", systemImage: "person.2")
                .frame(maxWidth: .infinity)
        } else {
            VStack(spacing: 0) {
                header
                ForEach(Array(ordered.enumerated()), id: \.element.id) { i, s in
                    Divider()
                    row(s, previous: i > 0 ? ordered[i - 1] : nil)
                }
            }
        }
    }

    private var header: some View {
        HStack {
            Text("Stage").frame(maxWidth: .infinity, alignment: .leading)
            Text("Count").frame(width: 60, alignment: .trailing)
            Text("Conv.").frame(width: 70, alignment: .trailing)
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.secondary)
        .padding(.vertical, 6)
    }

    private func row(_ s: FunnelStageCount, previous: FunnelStageCount?) -> some View {
        HStack {
            HStack(spacing: 8) {
                Circle().fill(Theme.stageColor(s.stageValue)).frame(width: 9, height: 9)
                Text(s.stageValue.label)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Text("\(s.count)").frame(width: 60, alignment: .trailing)
            Text(conversion(s, previous)).frame(width: 70, alignment: .trailing)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 8)
    }

    /// Percent of the stage below that reached this stage. "—" for the base stage.
    private func conversion(_ s: FunnelStageCount, _ previous: FunnelStageCount?) -> String {
        guard let previous, previous.count > 0 else { return "—" }
        return "\(Int((Double(s.count) / Double(previous.count) * 100).rounded()))%"
    }
}

private extension View {
    func cardBackground() -> some View {
        self.frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}
