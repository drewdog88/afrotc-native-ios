import SwiftUI
import Charts

/// Recruitment analytics, mirroring the web Pipeline page: a cumulative
/// reach-by-stage trend chart (week/month) with a crosshair + multi-series
/// tooltip and a clickable legend, plus a current funnel + stage conversion
/// table whose rows drill into the filtered roster.
struct PipelineView: View {
    @EnvironmentObject private var router: AppRouter
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

                VStack(alignment: .leading, spacing: 2) {
                    Text("Pipeline").font(.title2.bold())
                    Text("How the recruiting pipeline is building over time — cumulative recruits to reach each stage by \(interval == "week" ? "week" : "month").")
                        .font(.subheadline).foregroundStyle(.secondary)
                }

                if loading && funnel == nil {
                    skeleton
                } else {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("Cumulative reach by stage").font(.title3.bold())
                            Spacer()
                            Picker("Interval", selection: $interval) {
                                Text("Week").tag("week")
                                Text("Month").tag("month")
                            }
                            .pickerStyle(.segmented)
                            .frame(width: 160)
                        }
                        Text("Running total of recruits to reach each stage · one shared scale")
                            .font(.caption).foregroundStyle(.secondary)
                        TrendChart(points: cumulativePoints,
                                   onSelectStage: { router.openRecruits(stage: $0) })
                    }
                    .cardBackground()

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Stage conversion").font(.title3.bold())
                        Text("Current count per stage · share advancing from the stage below")
                            .font(.caption).foregroundStyle(.secondary)
                        ConversionTable(stages: funnel?.stages ?? [], total: funnel?.total ?? 0,
                                        onSelectStage: { router.openRecruits(stage: $0) })
                    }
                    .cardBackground()
                }
            }
            .padding(16)
        }
        .background(Color(.systemGroupedBackground))
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

    /// Redacted placeholders while the first load is in flight.
    private var skeleton: some View {
        VStack(spacing: 20) {
            ForEach([260.0, 220.0], id: \.self) { h in
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color(.secondarySystemGroupedBackground))
                    .frame(height: h)
            }
        }
        .redacted(reason: .placeholder)
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

/// Multi-series line chart, one line per stage in its brand color, with a
/// crosshair + multi-series tooltip on selection and a clickable legend.
private struct TrendChart: View {
    let points: [CumulativePoint]
    let onSelectStage: (RecruitStage) -> Void

    @State private var selectedPeriod: String?

    var body: some View {
        if points.isEmpty {
            ContentUnavailableView("No trend data yet",
                                   systemImage: "chart.xyaxis.line",
                                   description: Text("Advance recruits through stages to build the trend."))
                .frame(maxWidth: .infinity)
        } else {
            Chart(points) { p in
                LineMark(
                    x: .value("Period", p.period),
                    y: .value("Reached", p.total)
                )
                .foregroundStyle(by: .value("Stage", p.stage.label))
                .symbol(by: .value("Stage", p.stage.label))

                if let selectedPeriod, selectedPeriod == p.period {
                    PointMark(
                        x: .value("Period", p.period),
                        y: .value("Reached", p.total)
                    )
                    .foregroundStyle(Theme.stageColor(p.stage))
                    .symbolSize(90)
                }
            }
            .chartForegroundStyleScale(domain: stageDomain, range: stageRange)
            .chartXScale(domain: sortedPeriods)
            .chartLegend(.hidden)
            .chartXAxis { AxisMarks(values: .automatic(desiredCount: 4)) }
            .chartXSelection(value: $selectedPeriod)
            .chartBackground { proxy in
                // Dashed crosshair at the selected period.
                if let selectedPeriod, let x = proxy.position(forX: selectedPeriod) {
                    GeometryReader { geo in
                        let plot = geo[proxy.plotFrame!]
                        Rectangle()
                            .fill(Theme.muted.opacity(0.6))
                            .frame(width: 1, height: plot.height)
                            .position(x: plot.minX + x, y: plot.midY)
                    }
                }
            }
            .frame(height: 240)
            .overlay(alignment: .topLeading) {
                if let selectedPeriod {
                    tooltip(for: selectedPeriod)
                        .padding(8)
                }
            }

            // Interactive legend — tap a stage to open its filtered roster.
            legend
        }
    }

    private func tooltip(for period: String) -> some View {
        let rows = points.filter { $0.period == period }
            .sorted { $0.stage.funnelOrder < $1.stage.funnelOrder }
        return VStack(alignment: .leading, spacing: 3) {
            Text(period).font(.caption2.weight(.bold))
            ForEach(rows) { r in
                HStack(spacing: 6) {
                    Circle().fill(Theme.stageColor(r.stage)).frame(width: 7, height: 7)
                    Text(r.stage.label).font(.caption2)
                    Spacer(minLength: 8)
                    Text("\(r.total)").font(.caption2.weight(.bold))
                }
            }
        }
        .padding(8)
        .frame(width: 150)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.muted.opacity(0.2)))
    }

    private var legend: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(presentStages) { stage in
                    Button { onSelectStage(stage) } label: {
                        HStack(spacing: 6) {
                            Circle().fill(Theme.stageColor(stage)).frame(width: 8, height: 8)
                            Text(stage.label).font(.caption.weight(.medium))
                        }
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(Theme.stageColor(stage).opacity(0.12), in: Capsule())
                        .foregroundStyle(Theme.ink)
                    }
                    .buttonStyle(.plain)
                }
            }
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

    /// Chronologically-sorted, de-duplicated periods so the categorical x-axis
    /// runs left→right in time order instead of first-seen order.
    private var sortedPeriods: [String] {
        var seen: [String] = []
        for p in points.map(\.period).sorted() where !seen.contains(p) { seen.append(p) }
        return seen
    }
}

/// Stage / count / conversion-to-next table. Rows drill into the filtered roster.
private struct ConversionTable: View {
    let stages: [FunnelStageCount]
    let total: Int
    let onSelectStage: (RecruitStage) -> Void

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
                    Button { onSelectStage(s.stageValue) } label: {
                        row(s, previous: i > 0 ? ordered[i - 1] : nil)
                    }
                    .buttonStyle(.plain)
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
                VStack(alignment: .leading, spacing: 1) {
                    Text(s.stageValue.label).foregroundStyle(Theme.ink)
                    Text(s.stageValue.blurb)
                        .font(.caption2).foregroundStyle(.secondary).lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Text("\(s.count)").frame(width: 60, alignment: .trailing).foregroundStyle(Theme.ink)
            Text(conversion(s, previous)).frame(width: 70, alignment: .trailing)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 8)
        .contentShape(Rectangle())
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
