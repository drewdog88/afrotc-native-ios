import SwiftUI

/// Recruiter task queue grouped by urgency (Overdue / Today / Upcoming) with a
/// Done archive, mirroring the web Follow-ups page. Tapping the checkbox marks a
/// task complete. Recruit names are resolved from a lightweight recruits fetch.
struct FollowUpsView: View {
    @State private var followups: [FollowUpOut] = []
    @State private var recruitNames: [Int: String] = [:]
    @State private var error: String?
    @State private var loading = false
    @State private var completing: Set<Int> = []
    @State private var showingCreate = false
    @State private var editingFollowUp: FollowUpOut?
    @State private var deleteConfirmId: Int?

    var body: some View {
        List {
            if let error {
                Text(error).foregroundStyle(Theme.danger)
            }
            group("Overdue", overdue, tint: Theme.danger)
            group("Today", today, tint: Theme.accent)
            group("Upcoming", upcoming, tint: Theme.muted)
            if !done.isEmpty {
                Section("Done") {
                    ForEach(done) { f in row(f) }
                }
            }
            if followups.isEmpty && !loading && error == nil {
                ContentUnavailableView("No follow-ups", systemImage: "checklist")
            }
        }
        .listStyle(.insetGrouped)
        .overlay { if loading && followups.isEmpty { ProgressView() } }
        .navigationTitle("Follow-ups")
        .navigationDestination(for: RecruitRoute.self) { RecruitDetailView(recruitId: $0.id) }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingCreate = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingCreate) {
            FollowUpCreateSheet(recruitNames: recruitNames) { await load() }
        }
        .sheet(item: $editingFollowUp) { followup in
            FollowUpEditSheet(followup: followup, recruitNames: recruitNames) { await load() }
        }
        .confirmationDialog("Delete this follow-up?", isPresented: .constant(deleteConfirmId != nil), presenting: deleteConfirmId) { id in
            Button("Delete", role: .destructive) {
                Task { await delete(id: id) }
            }
        }
        .task { await load() }
        .refreshable { await load() }
    }

    @ViewBuilder
    private func group(_ title: String, _ items: [FollowUpOut], tint: Color) -> some View {
        if !items.isEmpty {
            Section {
                ForEach(items) { f in row(f) }
            } header: {
                HStack {
                    Text(title)
                    Spacer()
                    Text("\(items.count)").foregroundStyle(tint)
                }
            }
        }
    }

    @ViewBuilder
    private func row(_ f: FollowUpOut) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Button {
                Task { await toggleComplete(f) }
            } label: {
                Image(systemName: f.isDone ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundStyle(f.isDone ? Theme.ok : Theme.muted)
            }
            .buttonStyle(.plain)
            .disabled(completing.contains(f.id))

            VStack(alignment: .leading, spacing: 3) {
                Text(f.note)
                    .strikethrough(f.isDone)
                    .foregroundStyle(f.isDone ? .secondary : .primary)
                Text(dueLabel(f)).font(.caption).foregroundStyle(.secondary)
                if let rid = f.recruitId {
                    NavigationLink(value: RecruitRoute(id: rid)) {
                        Text(recruitNames[rid] ?? "Recruit #\(rid)")
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 8).padding(.vertical, 2)
                            .background(Theme.ink.opacity(0.08), in: Capsule())
                            .foregroundStyle(Theme.ink)
                    }
                    .buttonStyle(.plain)
                }
            }
            Spacer()
        }
        .padding(.vertical, 2)
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button(role: .destructive) {
                deleteConfirmId = f.id
            } label: {
                Label("Delete", systemImage: "trash")
            }
            if !f.isDone {
                Button {
                    editingFollowUp = f
                } label: {
                    Label("Edit", systemImage: "pencil")
                }
                .tint(.blue)
            }
        }
    }

    private func dueLabel(_ f: FollowUpOut) -> String {
        if f.isDone { return "Completed \(DateDisplay.mediumDate(f.completedAt))" }
        return "Due \(DateDisplay.mediumDateTime(f.dueDate))"
    }

    // MARK: - Grouping

    private var startOfToday: Date { Calendar.current.startOfDay(for: .now) }
    private var startOfTomorrow: Date { Calendar.current.date(byAdding: .day, value: 1, to: startOfToday)! }

    private var open: [FollowUpOut] {
        followups.filter { !$0.isDone }.sorted { $0.dueDate < $1.dueDate }
    }
    private var overdue: [FollowUpOut] {
        open.filter { (DateDisplay.parseDateTime($0.dueDate) ?? .distantFuture) < startOfToday }
    }
    private var today: [FollowUpOut] {
        open.filter {
            let d = DateDisplay.parseDateTime($0.dueDate) ?? .distantFuture
            return d >= startOfToday && d < startOfTomorrow
        }
    }
    private var upcoming: [FollowUpOut] {
        open.filter { (DateDisplay.parseDateTime($0.dueDate) ?? .distantPast) >= startOfTomorrow }
    }
    private var done: [FollowUpOut] {
        followups.filter { $0.isDone }
            .sorted { ($0.completedAt ?? $0.dueDate) > ($1.completedAt ?? $1.dueDate) }
    }

    // MARK: - Actions

    private func toggleComplete(_ f: FollowUpOut) async {
        completing.insert(f.id)
        defer { completing.remove(f.id) }
        do {
            let updated: FollowUpOut
            if f.isDone {
                // Reopen: set status back to "open"
                updated = try await APIClient.shared.updateFollowup(id: f.id, FollowUpUpdateInput(status: "open"))
            } else {
                // Complete
                updated = try await APIClient.shared.completeFollowup(id: f.id)
            }
            if let i = followups.firstIndex(where: { $0.id == f.id }) { followups[i] = updated }
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func delete(id: Int) async {
        do {
            try await APIClient.shared.deleteFollowup(id: id)
            followups.removeAll { $0.id == id }
            deleteConfirmId = nil
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            async let fus = APIClient.shared.followups().items
            async let recs = APIClient.shared.recruits().items
            followups = try await fus
            recruitNames = Dictionary(uniqueKeysWithValues: try await recs.map { ($0.id, $0.fullName) })
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

// MARK: - Create Sheet

private struct FollowUpCreateSheet: View {
    let recruitNames: [Int: String]
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var note = ""
    @State private var dueDate = Date()
    @State private var selectedRecruitId: Int?
    @State private var availableRecruits: [(Int, String)] = []
    @State private var saving = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Note", text: $note, axis: .vertical)
                        .lineLimit(3...6)
                    DatePicker("Due Date", selection: $dueDate, displayedComponents: [.date, .hourAndMinute])
                } header: {
                    Text("Details")
                }

                Section {
                    Picker("Recruit (optional)", selection: $selectedRecruitId) {
                        Text("None").tag(nil as Int?)
                        ForEach(availableRecruits, id: \.0) { id, name in
                            Text(name).tag(id as Int?)
                        }
                    }
                } header: {
                    Text("Link to Recruit")
                }

                if let error {
                    Section {
                        Text(error).foregroundStyle(Theme.danger)
                    }
                }
            }
            .navigationTitle("New Follow-up")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || saving)
                }
            }
            .task { await loadRecruits() }
        }
    }

    private func loadRecruits() async {
        do {
            let recruits = try await APIClient.shared.recruits(limit: 200).items
            availableRecruits = recruits.map { ($0.id, $0.fullName) }.sorted { $0.1 < $1.1 }
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func save() async {
        guard !note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        saving = true
        error = nil
        defer { saving = false }
        do {
            let dueDateString = ISO8601DateFormatter().string(from: dueDate)
            let input = FollowUpCreateInput(
                note: note.trimmingCharacters(in: .whitespacesAndNewlines),
                dueDate: dueDateString,
                status: "open",
                recruitId: selectedRecruitId
            )
            _ = try await APIClient.shared.createFollowup(input)
            await onSave()
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

// MARK: - Edit Sheet

private struct FollowUpEditSheet: View {
    let followup: FollowUpOut
    let recruitNames: [Int: String]
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var note = ""
    @State private var dueDate = Date()
    @State private var selectedRecruitId: Int?
    @State private var availableRecruits: [(Int, String)] = []
    @State private var saving = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Note", text: $note, axis: .vertical)
                        .lineLimit(3...6)
                    DatePicker("Due Date", selection: $dueDate, displayedComponents: [.date, .hourAndMinute])
                } header: {
                    Text("Details")
                }

                Section {
                    Picker("Recruit (optional)", selection: $selectedRecruitId) {
                        Text("None").tag(nil as Int?)
                        ForEach(availableRecruits, id: \.0) { id, name in
                            Text(name).tag(id as Int?)
                        }
                    }
                } header: {
                    Text("Link to Recruit")
                }

                if let error {
                    Section {
                        Text(error).foregroundStyle(Theme.danger)
                    }
                }
            }
            .navigationTitle("Edit Follow-up")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || saving)
                }
            }
            .task {
                note = followup.note
                if let parsedDate = DateDisplay.parseDateTime(followup.dueDate) {
                    dueDate = parsedDate
                }
                selectedRecruitId = followup.recruitId
                await loadRecruits()
            }
        }
    }

    private func loadRecruits() async {
        do {
            let recruits = try await APIClient.shared.recruits(limit: 200).items
            availableRecruits = recruits.map { ($0.id, $0.fullName) }.sorted { $0.1 < $1.1 }
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func save() async {
        guard !note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        saving = true
        error = nil
        defer { saving = false }
        do {
            let dueDateString = ISO8601DateFormatter().string(from: dueDate)
            let input = FollowUpUpdateInput(
                note: note.trimmingCharacters(in: .whitespacesAndNewlines),
                dueDate: dueDateString,
                recruitId: selectedRecruitId
            )
            _ = try await APIClient.shared.updateFollowup(id: followup.id, input)
            await onSave()
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
