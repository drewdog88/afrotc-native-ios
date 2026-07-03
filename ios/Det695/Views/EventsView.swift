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
    @State private var showingCreateSheet = false

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
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                if let error {
                    Section {
                        Text(error).foregroundStyle(Theme.danger)
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
            await onSave()
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
