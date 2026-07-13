import SwiftUI

/// Typed navigation route for an event detail (kept distinct from other Int
/// routes so several screens can share one NavigationStack in the More tab).
struct EventRoute: Hashable { let id: Int }

/// Outreach events, mirroring the web Events page: flip between a month calendar
/// (event pills on each day, today highlighted, prev/next/Today nav) and a
/// chronological Upcoming / Past list, scoped by a status filter. Rows and pills
/// both push a detail.
struct EventsView: View {
    private enum ViewMode: String, CaseIterable {
        case calendar, list
        var label: String { rawValue.capitalized }
    }

    @State private var events: [EventOut] = []
    @State private var status: EventStatus?
    @State private var error: String?
    @State private var loading = false
    @State private var showingCreateSheet = false
    @State private var mode: ViewMode = .calendar

    var body: some View {
        VStack(spacing: 0) {
            Picker("View", selection: $mode) {
                ForEach(ViewMode.allCases, id: \.self) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding([.horizontal, .top])

            if let error {
                Text(error).foregroundStyle(Theme.danger)
                    .font(.footnote)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal)
            }

            switch mode {
            case .calendar:
                MonthCalendar(events: events)
            case .list:
                eventList
            }
        }
        .overlay { if loading && events.isEmpty { ProgressView() } }
        .navigationTitle("Events")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: EventRoute.self) { EventDetailView(eventId: $0.id) }
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    showingCreateSheet = true
                } label: {
                    Label("Add", systemImage: "plus")
                }
            }
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
        .sheet(isPresented: $showingCreateSheet) {
            EventFormSheet(mode: .create) {
                await load()
            }
        }
        .task(id: status?.rawValue ?? "") { await load() }
        .refreshable { await load() }
    }

    /// The chronological list mode: Upcoming / Past sections.
    private var eventList: some View {
        List {
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
                ContentUnavailableView(status == nil ? "No events" : "No matches",
                                       systemImage: "calendar",
                                       description: Text(status == nil
                                            ? "Add your first event to start the calendar."
                                            : "No events match this status."))
            }
        }
        .listStyle(.insetGrouped)
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

// MARK: - Calendar

/// A month grid mirroring the web calendar: a 6-week (42-cell) grid starting on
/// the Sunday on/before the 1st, with each day showing up to three event pills
/// (color-coded by status) and today highlighted. Prev/next/Today step the month.
private struct MonthCalendar: View {
    let events: [EventOut]

    /// The first day of the month currently shown.
    @State private var monthStart: Date = Calendar.current.dateInterval(of: .month, for: .now)?.start
        ?? Calendar.current.startOfDay(for: .now)

    private let calendar = Calendar.current
    private let weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    /// Events bucketed by their "yyyy-MM-dd" day, each list sorted by start time.
    private var byDay: [String: [EventOut]] {
        var map: [String: [EventOut]] = [:]
        for e in events {
            map[String(e.eventDate.prefix(10)), default: []].append(e)
        }
        for key in map.keys {
            map[key]?.sort { ($0.startTime ?? "") < ($1.startTime ?? "") }
        }
        return map
    }

    /// The 42 day-cells: the Sunday on/before the 1st, then 41 consecutive days.
    private var cells: [Date] {
        let weekday = calendar.component(.weekday, from: monthStart) // 1 = Sunday
        let start = calendar.date(byAdding: .day, value: -(weekday - 1), to: monthStart) ?? monthStart
        return (0..<42).compactMap { calendar.date(byAdding: .day, value: $0, to: start) }
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            weekdayRow
            grid
            Spacer(minLength: 0)
        }
        .padding(.horizontal)
    }

    private var header: some View {
        HStack {
            Text(monthTitle).font(.title3.weight(.semibold))
            Spacer()
            Button("Today") { step(toCurrentMonth: true) }
                .font(.subheadline)
            Button { step(by: -1) } label: { Image(systemName: "chevron.left") }
                .accessibilityLabel("Previous month")
            Button { step(by: 1) } label: { Image(systemName: "chevron.right") }
                .accessibilityLabel("Next month")
        }
        .padding(.vertical, 12)
    }

    private var weekdayRow: some View {
        HStack(spacing: 2) {
            ForEach(weekdays, id: \.self) { w in
                Text(w)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding(.bottom, 4)
    }

    private var grid: some View {
        let columns = Array(repeating: GridItem(.flexible(), spacing: 2), count: 7)
        return LazyVGrid(columns: columns, spacing: 2) {
            ForEach(cells, id: \.self) { day in
                DayCell(day: day,
                        inMonth: calendar.isDate(day, equalTo: monthStart, toGranularity: .month),
                        isToday: calendar.isDateInToday(day),
                        events: byDay[key(day)] ?? [])
            }
        }
    }

    private var monthTitle: String {
        monthStart.formatted(.dateTime.month(.wide).year())
    }

    private func key(_ day: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: day)
    }

    private func step(by months: Int) {
        if let d = calendar.date(byAdding: .month, value: months, to: monthStart) { monthStart = d }
    }

    private func step(toCurrentMonth: Bool) {
        monthStart = calendar.dateInterval(of: .month, for: .now)?.start
            ?? calendar.startOfDay(for: .now)
    }
}

/// A single day in the month grid: the date number (highlighted when today) and
/// up to three event pills, with a "+N more" overflow marker.
private struct DayCell: View {
    let day: Date
    let inMonth: Bool
    let isToday: Bool
    let events: [EventOut]

    private var dayNumber: String { day.formatted(.dateTime.day()) }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(dayNumber)
                .font(.caption2)
                .fontWeight(isToday ? .bold : .regular)
                .foregroundStyle(numberColor)
                .frame(width: 20, height: 20)
                .background { if isToday { Circle().fill(Theme.accent) } }
                .frame(maxWidth: .infinity, alignment: .leading)

            ForEach(events.prefix(3)) { e in
                NavigationLink(value: EventRoute(id: e.id)) { pill(e) }
                    .buttonStyle(.plain)
            }
            if events.count > 3 {
                Text("+\(events.count - 3)")
                    .font(.system(size: 9))
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .padding(3)
        .frame(maxWidth: .infinity, minHeight: 64, alignment: .topLeading)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color(.secondarySystemBackground)))
        .opacity(inMonth ? 1 : 0.4)
    }

    private var numberColor: Color {
        if isToday { return .white }
        return inMonth ? .primary : .secondary
    }

    private func pill(_ e: EventOut) -> some View {
        HStack(spacing: 2) {
            Circle()
                .fill(Theme.eventStatusColor(e.statusValue))
                .frame(width: 5, height: 5)
            Text(e.title)
                .font(.system(size: 9))
                .lineLimit(1)
                .foregroundStyle(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 3)
        .padding(.vertical, 1)
        .background(RoundedRectangle(cornerRadius: 3).fill(Theme.eventStatusColor(e.statusValue).opacity(0.15)))
    }
}

private struct EventRow: View {
    let event: EventOut

    var body: some View {
        HStack(spacing: 12) {
            EventDateChip(dateString: event.eventDate, tint: Theme.eventStatusColor(event.statusValue))
            VStack(alignment: .leading, spacing: 2) {
                Text(event.title).font(.body.weight(.semibold))
                Text(subtitle).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            EventStatusPill(status: event.statusValue)
        }
        .padding(.vertical, 4)
    }

    private var subtitle: String {
        var parts: [String] = []
        if let t = DateDisplay.time(event.startTime) { parts.append(t) }
        if let loc = event.location, !loc.isEmpty { parts.append(loc) }
        if parts.isEmpty { parts.append(event.eventType) }
        return parts.joined(separator: " · ")
    }
}

/// A month/day date box mirroring the web `dateChip` (tinted month abbreviation
/// stacked over a bold day number).
struct EventDateChip: View {
    let dateString: String
    let tint: Color

    var body: some View {
        VStack(spacing: 0) {
            Text(month).font(.caption2.weight(.bold)).foregroundStyle(tint)
            Text(day).font(.headline).foregroundStyle(Theme.ink)
        }
        .frame(width: 44, height: 44)
        .background(RoundedRectangle(cornerRadius: 8).fill(tint.opacity(0.12)))
    }

    private var parsed: Date? { DateDisplay.parseDay(dateString) }
    private var month: String {
        guard let d = parsed else { return "—" }
        return Self.monthFormatter.string(from: d).uppercased()
    }
    private var day: String {
        guard let d = parsed else { return "?" }
        return Self.dayFormatter.string(from: d)
    }

    private static let monthFormatter: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "MMM"; return f
    }()
    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "d"; return f
    }()
}

/// A tinted status capsule for event rows, mirroring the web status tag.
struct EventStatusPill: View {
    let status: EventStatus
    var body: some View {
        Text(status.label)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(Theme.eventStatusColor(status).opacity(0.18), in: Capsule())
            .foregroundStyle(Theme.eventStatusColor(status))
    }
}

/// Event detail with edit and delete actions.
struct EventDetailView: View {
    let eventId: Int
    @State private var event: EventOut?
    @State private var error: String?
    @State private var showingEditSheet = false
    @State private var showingDeleteConfirm = false
    @Environment(\.dismiss) private var dismiss

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
                    Section {
                        Button(role: .destructive) {
                            showingDeleteConfirm = true
                        } label: {
                            HStack {
                                Spacer()
                                Text("Delete event")
                                Spacer()
                            }
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
        .navigationTitle(event?.title ?? "Event")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit") {
                    showingEditSheet = true
                }
                .disabled(event == nil)
            }
        }
        .sheet(isPresented: $showingEditSheet) {
            if let e = event {
                EventFormSheet(mode: .edit(e)) {
                    await load()
                }
            }
        }
        .confirmationDialog("Delete this event?", isPresented: $showingDeleteConfirm, titleVisibility: .visible) {
            Button("Delete", role: .destructive) {
                Task { await deleteEvent() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This action cannot be undone.")
        }
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

    private func deleteEvent() async {
        do {
            try await APIClient.shared.deleteEvent(id: eventId)
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Shared form sheet for creating or editing an event.
private struct EventFormSheet: View {
    enum Mode {
        case create
        case edit(EventOut)
    }

    let mode: Mode
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var eventType = ""
    @State private var eventDate = Date()
    @State private var startTime: Date?
    @State private var endTime: Date?
    @State private var description = ""
    @State private var location = ""
    @State private var attendeesCount = 0
    @State private var notes = ""
    @State private var status = EventStatus.scheduled
    @State private var saving = false
    @State private var saved = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                if let error {
                    Section {
                        Text(error).foregroundStyle(Theme.danger)
                    }
                }
                if saved {
                    Section {
                        Label("Saved", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(Theme.ok)
                    }
                }

                Section("Required") {
                    TextField("Title", text: $title)
                    TextField("Event type", text: $eventType)
                    DatePicker("Event date", selection: $eventDate, displayedComponents: .date)
                }

                Section("Status") {
                    Picker("Status", selection: $status) {
                        ForEach(EventStatus.allCases) { s in
                            Text(s.label).tag(s)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Section("Time") {
                    Toggle("Has start time", isOn: Binding(
                        get: { startTime != nil },
                        set: { startTime = $0 ? Date() : nil }
                    ))
                    if startTime != nil {
                        DatePicker("Start time", selection: Binding(
                            get: { startTime ?? Date() },
                            set: { startTime = $0 }
                        ), displayedComponents: .hourAndMinute)
                    }

                    Toggle("Has end time", isOn: Binding(
                        get: { endTime != nil },
                        set: { endTime = $0 ? Date() : nil }
                    ))
                    if endTime != nil {
                        DatePicker("End time", selection: Binding(
                            get: { endTime ?? Date() },
                            set: { endTime = $0 }
                        ), displayedComponents: .hourAndMinute)
                    }
                }

                Section("Details") {
                    TextField("Location", text: $location)
                    Stepper("Attendees: \(attendeesCount)", value: $attendeesCount, in: 0...9999)
                    TextField("Description", text: $description, axis: .vertical)
                        .lineLimit(3...6)
                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle(mode.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .disabled(saving)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(saving || !isValid)
                }
            }
            .onAppear { prefillIfNeeded() }
        }
    }

    private var isValid: Bool {
        !title.isEmpty && !eventType.isEmpty
    }

    private func prefillIfNeeded() {
        guard case .edit(let event) = mode else { return }
        title = event.title
        eventType = event.eventType
        status = event.statusValue
        attendeesCount = event.attendeesCount
        description = event.description ?? ""
        location = event.location ?? ""
        notes = event.notes ?? ""

        // Parse eventDate "yyyy-MM-dd"
        if let parsed = Self.dayFormatter.date(from: event.eventDate) {
            eventDate = parsed
        }

        // Parse startTime "HH:mm:ss"
        if let st = event.startTime, !st.isEmpty,
           let parsed = Self.timeFormatter.date(from: st) {
            startTime = parsed
        }

        // Parse endTime "HH:mm:ss"
        if let et = event.endTime, !et.isEmpty,
           let parsed = Self.timeFormatter.date(from: et) {
            endTime = parsed
        }
    }

    private func save() async {
        saving = true
        error = nil
        defer { saving = false }

        do {
            let eventDateString = Self.dayFormatter.string(from: eventDate)
            let startTimeString = startTime.map { Self.timeFormatter.string(from: $0) }
            let endTimeString = endTime.map { Self.timeFormatter.string(from: $0) }

            switch mode {
            case .create:
                let input = EventCreateInput(
                    title: title,
                    eventDate: eventDateString,
                    eventType: eventType,
                    status: status.rawValue,
                    attendeesCount: attendeesCount,
                    description: description.isEmpty ? nil : description,
                    startTime: startTimeString,
                    endTime: endTimeString,
                    location: location.isEmpty ? nil : location,
                    universityId: nil,
                    notes: notes.isEmpty ? nil : notes
                )
                _ = try await APIClient.shared.createEvent(input)
            case .edit(let event):
                let input = EventUpdateInput(
                    title: title,
                    eventDate: eventDateString,
                    eventType: eventType,
                    status: status.rawValue,
                    attendeesCount: attendeesCount,
                    description: description.isEmpty ? nil : description,
                    startTime: startTimeString,
                    endTime: endTimeString,
                    location: location.isEmpty ? nil : location,
                    universityId: nil,
                    notes: notes.isEmpty ? nil : notes
                )
                _ = try await APIClient.shared.updateEvent(id: event.id, input)
            }
            saved = true
            await onSave()
            // Brief success flash before the sheet closes.
            try? await Task.sleep(nanoseconds: 500_000_000)
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    /// Fixed formatter for "yyyy-MM-dd" date strings, with en_US_POSIX locale.
    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }()

    /// Fixed formatter for "HH:mm:ss" time strings, with en_US_POSIX locale.
    private static let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "HH:mm:ss"
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }()
}

private extension EventFormSheet.Mode {
    var title: String {
        switch self {
        case .create: return "New Event"
        case .edit: return "Edit Event"
        }
    }
}

// `LabeledRow` and `LinkRow` are declared once, module-wide, in ContactsView.swift.
