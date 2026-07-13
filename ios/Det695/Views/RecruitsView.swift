import SwiftUI

/// Typed navigation route to a recruit detail, distinct from other Int routes.
struct RecruitRoute: Hashable { let id: Int }

/// Recruits list with search + stage filter, mirroring the web Recruits page.
struct RecruitsView: View {
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var session: Session
    @State private var recruits: [RecruitOut] = []
    @State private var total = 0
    @State private var search = ""
    @State private var stage: RecruitStage?
    @State private var error: String?
    @State private var loading = false
    @State private var showCreate = false
    @State private var showImport = false

    private var canWrite: Bool { (session.user?.role ?? "viewer") != "viewer" }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    StageFilterChips(stage: $stage)
                        .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 4, trailing: 0))
                        .listRowSeparator(.hidden)
                }
                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                }
                ForEach(recruits) { r in
                    NavigationLink(value: RecruitRoute(id: r.id)) { RecruitRow(recruit: r) }
                }
                if recruits.isEmpty && !loading && error == nil {
                    ContentUnavailableView {
                        Label(isFiltered ? "No matches" : "No recruits yet", systemImage: "person.2")
                    } description: {
                        Text(isFiltered
                             ? "No recruits match this view."
                             : "Add your first prospect to get started.")
                    }
                    .listRowSeparator(.hidden)
                }
                if !recruits.isEmpty {
                    Text(countLabel)
                        .font(.footnote).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                        .listRowSeparator(.hidden)
                }
            }
            .listStyle(.plain)
            .overlay { if loading && recruits.isEmpty { ProgressView() } }
            .navigationTitle("Recruits")
            .navigationBarTitleDisplayMode(.inline)
            .det695BrandBar()
            .navigationDestination(for: RecruitRoute.self) { RecruitDetailView(recruitId: $0.id) }
            .searchable(text: $search, prompt: "Search recruits")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            showCreate = true
                        } label: {
                            Label("Add recruit", systemImage: "plus")
                        }
                        if canWrite {
                            Button {
                                showImport = true
                            } label: {
                                Label("Import from file", systemImage: "square.and.arrow.down")
                            }
                        }
                    } label: {
                        Label("Add", systemImage: "plus")
                    }
                }
            }
            .task(id: filterKey) { await load() }
            .refreshable { await load() }
            .sheet(isPresented: $showCreate) {
                RecruitFormSheet(mode: .create) { await load() }
            }
            .sheet(isPresented: $showImport) {
                ImportRecruitsView { Task { await load() } }
            }
            .onAppear {
                if let pendingStage = router.pendingRecruitStage {
                    stage = pendingStage
                    router.pendingRecruitStage = nil
                }
            }
            .onChange(of: router.pendingRecruitStage) { oldValue, newValue in
                if let newStage = newValue {
                    stage = newStage
                    router.pendingRecruitStage = nil
                }
            }
        }
    }

    private var filterKey: String { "\(search)|\(stage?.rawValue ?? "")" }
    private var isFiltered: Bool { !search.isEmpty || stage != nil }

    /// Short school-type label for tight spaces (list rows).
    static func schoolTypeShort(_ raw: String) -> String {
        switch raw.lowercased() {
        case "high_school": return "HS"
        case "college", "university": return "College"
        default: return raw.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private var countLabel: String {
        let shown = recruits.count
        let suffix = total > shown ? " of \(total)" : ""
        return "\(shown)\(suffix) recruit\(total == 1 ? "" : "s")"
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            let page = try await APIClient.shared.recruits(search: search, stage: stage)
            recruits = page.items
            total = page.total
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Horizontally-scrolling stage filter chips (All + each stage), mirroring the
/// web Recruits chip row. Tapping the active chip clears the filter.
private struct StageFilterChips: View {
    @Binding var stage: RecruitStage?

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                chip(label: "All", active: stage == nil, tint: Theme.ink) { stage = nil }
                ForEach(RecruitStage.allCases) { s in
                    chip(label: s.label, active: stage == s, tint: Theme.stageColor(s)) {
                        stage = (stage == s) ? nil : s
                    }
                }
            }
            .padding(.horizontal, 16)
        }
    }

    private func chip(label: String, active: Bool, tint: Color, tap: @escaping () -> Void) -> some View {
        Button(action: tap) {
            Text(label)
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 12).padding(.vertical, 6)
                .background(active ? tint : tint.opacity(0.12), in: Capsule())
                .foregroundStyle(active ? .white : tint)
        }
        .buttonStyle(.plain)
    }
}

private struct RecruitRow: View {
    let recruit: RecruitOut

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(recruit.fullName).font(.body.weight(.semibold))
                HStack(spacing: 6) {
                    Text(recruit.currentSchool)
                    Text("·")
                    Text(RecruitsView.schoolTypeShort(recruit.schoolType))
                }
                .font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            StageBadge(stage: recruit.stageValue)
        }
        .padding(.vertical, 4)
    }
}

struct StageBadge: View {
    let stage: RecruitStage
    var body: some View {
        Text(stage.label)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(Theme.stageColor(stage).opacity(0.18), in: Capsule())
            .foregroundStyle(Theme.stageColor(stage))
    }
}

/// Read-only recruit detail: profile fields plus the stage-transition history,
/// mirroring the web RecruitDetail page. Both are fetched fresh by id.
struct RecruitDetailView: View {
    let recruitId: Int
    @Environment(\.dismiss) private var dismiss
    @State private var recruit: RecruitOut?
    @State private var history: [StageEvent] = []
    @State private var error: String?
    @State private var showEdit = false
    @State private var showDeleteConfirm = false
    @State private var showStageChange = false
    @State private var stageError: String?
    @State private var deleting = false

    var body: some View {
        Group {
            if let r = recruit {
                Form {
                    if let stageError {
                        Section { Text(stageError).foregroundStyle(Theme.danger) }
                    }
                    Section {
                        LabeledRow("Name", r.fullName)
                        Button {
                            stageError = nil
                            showStageChange = true
                        } label: {
                            HStack {
                                Text("Stage").foregroundStyle(.secondary)
                                Spacer()
                                StageBadge(stage: r.stageValue)
                                Image(systemName: "chevron.right")
                                    .font(.caption2).foregroundStyle(.tertiary)
                            }
                        }
                        .tint(.primary)
                        LabeledRow("School", r.currentSchool)
                        LabeledRow("Type", schoolTypeLabel(r.schoolType))
                        if let m = r.major, !m.isEmpty { LabeledRow("Major", m) }
                        if let g = r.gpa { LabeledRow("GPA", String(format: "%.2f", g)) }
                    }
                    Section("Reach") {
                        if let e = r.email, !e.isEmpty {
                            LinkRow(label: "Email", value: e, url: URL(string: "mailto:\(e)"))
                        }
                        if let p = r.phone, !p.isEmpty {
                            LinkRow(label: "Phone", value: p,
                                    url: URL(string: "tel:\(p.filter { $0.isNumber || $0 == "+" })"))
                        }
                    }
                    if let i = r.interests, !i.isEmpty {
                        Section("Interests") { Text(i) }
                    }
                    if let n = r.notes, !n.isEmpty {
                        Section("Notes") { Text(n) }
                    }
                    Section {
                        Button(role: .destructive, action: { showDeleteConfirm = true }) {
                            HStack {
                                if deleting {
                                    ProgressView()
                                } else {
                                    Text("Delete recruit")
                                }
                            }
                        }
                        .disabled(deleting)
                    }
                    Section("Stage history") {
                        if history.isEmpty {
                            Text("No transitions recorded").foregroundStyle(.secondary)
                        } else {
                            ForEach(history) { StageEventRow(event: $0) }
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
        .navigationTitle(recruit?.fullName ?? "Recruit")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit") { showEdit = true }
                    .disabled(recruit == nil)
            }
        }
        .sheet(isPresented: $showEdit) {
            if let r = recruit {
                RecruitFormSheet(mode: .edit(r)) { await load() }
            }
        }
        .confirmationDialog("Delete this recruit?", isPresented: $showDeleteConfirm, titleVisibility: .visible) {
            Button("Delete \(recruit?.fullName ?? "recruit")", role: .destructive) {
                Task { await deleteRecruit() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This permanently removes \(recruit?.fullName ?? "this recruit") and their stage history. This can't be undone.")
        }
        .sheet(isPresented: $showStageChange) {
            if let r = recruit {
                StageChangeSheet(recruit: r) { newStage, note in
                    await changeStage(to: newStage, note: note)
                }
            }
        }
        .task { await load() }
    }

    private func schoolTypeLabel(_ raw: String) -> String {
        switch raw.lowercased() {
        case "high_school": return "High school"
        case "college", "university": return "College"
        default: return raw.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private func load() async {
        do {
            async let r = APIClient.shared.recruit(id: recruitId)
            async let h = APIClient.shared.recruitStageHistory(id: recruitId)
            recruit = try await r
            history = (try? await h) ?? []
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func changeStage(to newStage: RecruitStage, note: String?) async {
        guard let current = recruit, current.stageValue != newStage else { return }
        stageError = nil
        do {
            recruit = try await APIClient.shared.changeRecruitStage(
                id: recruitId, toStage: newStage.rawValue, note: note)
            history = (try? await APIClient.shared.recruitStageHistory(id: recruitId)) ?? []
        } catch {
            stageError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func deleteRecruit() async {
        deleting = true
        defer { deleting = false }
        do {
            try await APIClient.shared.deleteRecruit(id: recruitId)
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// One stage transition: "From → To" with the date and optional note.
private struct StageEventRow: View {
    let event: StageEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                if let from = event.fromStageValue {
                    StageBadge(stage: from)
                    Image(systemName: "arrow.right").font(.caption2).foregroundStyle(.secondary)
                }
                StageBadge(stage: event.toStageValue)
                Spacer()
                Text(DateDisplay.mediumDate(event.changedAt))
                    .font(.caption).foregroundStyle(.secondary)
            }
            if let n = event.note, !n.isEmpty {
                Text(n).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

/// Advance a recruit to a new stage with an optional note, mirroring the web
/// stage-change control. The current stage is disabled; the note is written to
/// the RecruitStageEvent history.
private struct StageChangeSheet: View {
    let recruit: RecruitOut
    let onChange: (RecruitStage, String?) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selection: RecruitStage
    @State private var note = ""
    @State private var saving = false

    init(recruit: RecruitOut, onChange: @escaping (RecruitStage, String?) async -> Void) {
        self.recruit = recruit
        self.onChange = onChange
        _selection = State(initialValue: recruit.stageValue)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("New stage") {
                    ForEach(RecruitStage.allCases) { s in
                        Button {
                            selection = s
                        } label: {
                            HStack {
                                StageBadge(stage: s)
                                if s == recruit.stageValue {
                                    Text("current").font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                                if s == selection {
                                    Image(systemName: "checkmark").foregroundStyle(Theme.accent)
                                }
                            }
                        }
                        .tint(.primary)
                        .disabled(s == recruit.stageValue)
                    }
                }
                Section {
                    TextField("Note (optional)", text: $note, axis: .vertical)
                        .lineLimit(2...4)
                } header: {
                    Text("Note")
                } footer: {
                    Text("Added to \(recruit.fullName)'s stage history.")
                }
            }
            .navigationTitle("Change stage")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }.disabled(saving)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(saving ? "Saving…" : "Save") {
                        saving = true
                        Task {
                            let trimmed = note.trimmingCharacters(in: .whitespacesAndNewlines)
                            await onChange(selection, trimmed.isEmpty ? nil : trimmed)
                            dismiss()
                        }
                    }
                    .disabled(saving || selection == recruit.stageValue)
                }
            }
        }
    }
}

/// Reusable form sheet for creating and editing recruits.
private struct RecruitFormSheet: View {
    enum Mode {
        case create
        case edit(RecruitOut)

        var title: String {
            switch self {
            case .create: return "Add recruit"
            case .edit: return "Edit recruit"
            }
        }
    }

    let mode: Mode
    let onComplete: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var currentSchool = ""
    @State private var schoolType = "high_school"
    @State private var startingStage: RecruitStage = .lead
    @State private var email = ""
    @State private var phone = ""
    @State private var major = ""
    @State private var gpa = ""
    @State private var interests = ""
    @State private var notes = ""
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
                Section("Basic info") {
                    TextField("First name", text: $firstName)
                    TextField("Last name", text: $lastName)
                    TextField("Current school", text: $currentSchool)
                    Picker("School type", selection: $schoolType) {
                        Text("High school").tag("high_school")
                        Text("College").tag("college")
                    }
                    if case .create = mode {
                        Picker("Starting stage", selection: $startingStage) {
                            ForEach(RecruitStage.allCases) { s in
                                Text(s.label).tag(s)
                            }
                        }
                    }
                }
                Section("Contact") {
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                    TextField("Phone", text: $phone)
                        .textContentType(.telephoneNumber)
                        .keyboardType(.phonePad)
                }
                Section("Academics") {
                    TextField("Major", text: $major)
                    TextField("GPA", text: $gpa)
                        .keyboardType(.decimalPad)
                }
                Section("Additional") {
                    TextField("Interests", text: $interests, axis: .vertical)
                        .lineLimit(2...4)
                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(2...4)
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
                    Button(saving ? "Saving..." : "Save") {
                        Task { await save() }
                    }
                    .disabled(!isValid || saving)
                }
            }
            .onAppear { prefillForEdit() }
        }
    }

    private var isValid: Bool {
        !firstName.trimmingCharacters(in: .whitespaces).isEmpty &&
        !lastName.trimmingCharacters(in: .whitespaces).isEmpty &&
        !currentSchool.trimmingCharacters(in: .whitespaces).isEmpty
    }

    private func prefillForEdit() {
        guard case .edit(let r) = mode else { return }
        firstName = r.firstName
        lastName = r.lastName
        currentSchool = r.currentSchool
        schoolType = r.schoolType
        email = r.email ?? ""
        phone = r.phone ?? ""
        major = r.major ?? ""
        if let g = r.gpa { gpa = String(format: "%.2f", g) }
        interests = r.interests ?? ""
        notes = r.notes ?? ""
    }

    private func save() async {
        saving = true
        error = nil
        defer { saving = false }

        let trimmedEmail = email.trimmingCharacters(in: .whitespaces)
        let trimmedPhone = phone.trimmingCharacters(in: .whitespaces)
        let trimmedMajor = major.trimmingCharacters(in: .whitespaces)
        let trimmedInterests = interests.trimmingCharacters(in: .whitespaces)
        let trimmedNotes = notes.trimmingCharacters(in: .whitespaces)
        let parsedGpa = Double(gpa.trimmingCharacters(in: .whitespaces))

        do {
            switch mode {
            case .create:
                let input = RecruitCreateInput(
                    firstName: firstName.trimmingCharacters(in: .whitespaces),
                    lastName: lastName.trimmingCharacters(in: .whitespaces),
                    currentSchool: currentSchool.trimmingCharacters(in: .whitespaces),
                    schoolType: schoolType,
                    stage: startingStage.rawValue,
                    email: trimmedEmail.isEmpty ? nil : trimmedEmail,
                    phone: trimmedPhone.isEmpty ? nil : trimmedPhone,
                    major: trimmedMajor.isEmpty ? nil : trimmedMajor,
                    gpa: parsedGpa,
                    interests: trimmedInterests.isEmpty ? nil : trimmedInterests,
                    notes: trimmedNotes.isEmpty ? nil : trimmedNotes
                )
                _ = try await APIClient.shared.createRecruit(input)
            case .edit(let r):
                let input = RecruitUpdateInput(
                    firstName: firstName.trimmingCharacters(in: .whitespaces),
                    lastName: lastName.trimmingCharacters(in: .whitespaces),
                    currentSchool: currentSchool.trimmingCharacters(in: .whitespaces),
                    schoolType: schoolType,
                    email: trimmedEmail.isEmpty ? nil : trimmedEmail,
                    phone: trimmedPhone.isEmpty ? nil : trimmedPhone,
                    major: trimmedMajor.isEmpty ? nil : trimmedMajor,
                    gpa: parsedGpa,
                    interests: trimmedInterests.isEmpty ? nil : trimmedInterests,
                    notes: trimmedNotes.isEmpty ? nil : trimmedNotes
                )
                _ = try await APIClient.shared.updateRecruit(id: r.id, input)
            }
            await onComplete()
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
