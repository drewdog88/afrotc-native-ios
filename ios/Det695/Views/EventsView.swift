import SwiftUI

/// Typed navigation route for an event detail (kept distinct from other Int
/// routes so several screens can share one NavigationStack in the More tab).
struct EventRoute: Hashable { let id: Int }

/// Outreach events as a chronological list split into Upcoming / Past, with a
/// status filter, mirroring the web Events page (list mode). Rows push a detail.
struct EventsView: View {
    @State private var events: [EventOut] = []
    @State private var status: EventStatus?
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        List {
            if let error {
                Text(error).foregroundStyle(Theme.danger)
            }
            if !upcoming.isEmpty {
                Section("Upcoming") {
                    ForEach(upcoming) { e in
                        NavigationLink(value: EventRoute(id: e.id)) { EventRow(event: e) }
                    }
                }
            }
            if !past.isEmpty {
                Section("Past") {
                    ForEach(past) { e in
                        NavigationLink(value: EventRoute(id: e.id)) { EventRow(event: e) }
                    }
                }
            }
            if events.isEmpty && !loading && error == nil {
                ContentUnavailableView("No events", systemImage: "calendar")
            }
        }
        .listStyle(.insetGrouped)
        .overlay { if loading && events.isEmpty { ProgressView() } }
        .navigationTitle("Events")
        .navigationDestination(for: EventRoute.self) { EventDetailView(eventId: $0.id) }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("All statuses") { status = nil }
                    Divider()
                    ForEach(EventStatus.allCases) { s in
                        Button(s.label) { status = s }
                    }
                } label: {
                    Label(status?.label ?? "All", systemImage: "line.3.horizontal.decrease.circle")
                }
            }
        }
        .task(id: status?.rawValue ?? "") { await load() }
        .refreshable { await load() }
    }

    /// Today at 00:00, for the upcoming/past split.
    private var startOfToday: Date { Calendar.current.startOfDay(for: .now) }

    private var upcoming: [EventOut] {
        events.filter { (DateDisplay.parseDay($0.eventDate) ?? .distantPast) >= startOfToday }
            .sorted { $0.eventDate < $1.eventDate }
    }
    private var past: [EventOut] {
        events.filter { (DateDisplay.parseDay($0.eventDate) ?? .distantPast) < startOfToday }
            .sorted { $0.eventDate > $1.eventDate }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            events = try await APIClient.shared.events(status: status?.rawValue).items
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct EventRow: View {
    let event: EventOut

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(Theme.eventStatusColor(event.statusValue))
                .frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text(event.title).font(.body.weight(.semibold))
                Text(subtitle).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }

    private var subtitle: String {
        var parts = [DateDisplay.mediumDate(event.eventDate)]
        if let t = DateDisplay.time(event.startTime) { parts.append(t) }
        if let loc = event.location, !loc.isEmpty { parts.append(loc) }
        return parts.joined(separator: " · ")
    }
}

/// Read-only event detail, fetched fresh by id.
struct EventDetailView: View {
    let eventId: Int
    @State private var event: EventOut?
    @State private var error: String?

    var body: some View {
        Group {
            if let e = event {
                Form {
                    Section {
                        LabeledRow("Type", e.eventType)
                        LabeledRow("Status", e.statusValue.label)
                        LabeledRow("Attendees", "\(e.attendeesCount)")
                    }
                    Section("When") {
                        LabeledRow("Date", DateDisplay.mediumDate(e.eventDate))
                        if let range = timeRange(e) { LabeledRow("Time", range) }
                    }
                    Section("Where") {
                        if let loc = e.location, !loc.isEmpty { LabeledRow("Location", loc) }
                        if let lat = e.latitude, let lon = e.longitude {
                            LinkRow(label: "Map", value: "Open in Maps",
                                    url: URL(string: "https://maps.apple.com/?q=\(lat),\(lon)"))
                        }
                    }
                    if let d = e.description, !d.isEmpty { Section("Description") { Text(d) } }
                    if let n = e.notes, !n.isEmpty { Section("Notes") { Text(n) } }
                }
            } else if let error {
                ContentUnavailableView("Couldn't load", systemImage: "exclamationmark.triangle",
                                       description: Text(error))
            } else {
                ProgressView()
            }
        }
        .navigationTitle(event?.title ?? "Event")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func timeRange(_ e: EventOut) -> String? {
        let start = DateDisplay.time(e.startTime)
        let end = DateDisplay.time(e.endTime)
        switch (start, end) {
        case let (.some(s), .some(en)): return "\(s) – \(en)"
        case let (.some(s), .none): return s
        default: return nil
        }
    }

    private func load() async {
        do { event = try await APIClient.shared.event(id: eventId) }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }
}
