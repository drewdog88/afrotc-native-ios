import SwiftUI

/// Cadets directory with search + status filter (active / inactive / graduated),
/// mirroring the web Cadets page.
struct CadetsView: View {
    private static let statuses = ["active", "inactive", "graduated"]

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
                    CadetRow(cadet: c)
                }
                if cadets.isEmpty && !loading && error == nil {
                    ContentUnavailableView("No cadets", systemImage: "shield")
                }
            }
            .listStyle(.plain)
            .overlay { if loading && cadets.isEmpty { ProgressView() } }
            .navigationTitle("Cadets")
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
        }
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
