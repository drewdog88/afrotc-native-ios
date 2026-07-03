import Foundation

/// Current-snapshot funnel from `/analytics/funnel`. Reuses `FunnelStageCount`
/// (declared in Dashboard.swift).
struct FunnelResponse: Decodable {
    let stages: [FunnelStageCount]
    let total: Int
    var fromDate: String?
    var toDate: String?
}

/// One stage's time series in the trends response.
struct TrendSeries: Decodable, Identifiable {
    let stage: String
    let points: [TrendPoint]
    var id: String { stage }
    var stageValue: RecruitStage { .from(stage) }
}

/// Multi-series recruitment trend from `/analytics/trends`.
struct TrendsResponse: Decodable {
    let series: [TrendSeries]
    let interval: String
    var fromDate: String?
    var toDate: String?
}
