import Foundation

/// Count of recruits at a specific funnel stage (FunnelStageCount).
struct FunnelStageCount: Decodable, Identifiable {
    let stage: String
    let count: Int
    var id: String { stage }
    var stageValue: RecruitStage { .from(stage) }
}

/// A single point in a time series (TrendPoint): a period label + a count.
struct TrendPoint: Decodable, Identifiable {
    let period: String
    let count: Int
    var id: String { period }
}

/// One row of the cadets-by-status breakdown. The backend types this as
/// `dict[str, int | str]`, so `count` is decoded flexibly (Int, or a numeric
/// String) to stay robust to either representation.
struct CadetStatusCount: Decodable, Identifiable {
    let status: String
    let count: Int
    var id: String { status }

    private enum CodingKeys: String, CodingKey { case status, count }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        status = try c.decode(String.self, forKey: .status)
        if let n = try? c.decode(Int.self, forKey: .count) {
            count = n
        } else if let s = try? c.decode(String.self, forKey: .count), let n = Int(s) {
            count = n
        } else {
            count = 0
        }
    }
}

/// Summary statistics for the dashboard overview (DashboardStats).
struct DashboardStats: Decodable {
    let totalRecruits: Int
    let recruitsByStage: [FunnelStageCount]
    let totalCadets: Int
    let cadetsByStatus: [CadetStatusCount]
    let openFollowups: Int
    let recentTrend: [TrendPoint]
}
