import SwiftUI

/// Typed navigation route to a recruit detail, distinct from other Int routes.
struct RecruitRoute: Hashable { let id: Int }

/// Recruits list with search + stage filter, mirroring the web Recruits page.
struct RecruitsView: View {
    @EnvironmentObject private var router: AppRouter
    @State private var recruits: [RecruitOut] = []
    @State private var search = ""
    @State private var stage: RecruitStage?
    @State private var error: String?
    @State private var loading = false
    @State private var showCreate = false

    var body: some View {
        NavigationStack {
            List {
                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                }
                ForEach(recruits) { r in
                    NavigationLink(value: RecruitRoute(id: r.id)) { RecruitRow(recruit: r) }
                }
                if recruits.isEmpty && !loading && error == nil {
                    ContentUnavailableView("No recruits", systemImage: "person.2")
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
                    Button {
                        showCreate = true
                    } label: {
                        Label("Add", systemImage: "plus")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("All stages") { stage = nil }
                        Divider()
                        ForEach(RecruitStage.allCases) { s in
                            Button(s.label) { stage = s }
                        }
                    } label: {
                        Label(stage?.label ?? "All", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
            .task(id: filterKey) { await load() }
            .refreshable { await load() }
            .sheet(isPresented: $showCreate) {
                RecruitFormSheet(mode: .create) { await load() }
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

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            recruits = try await APIClient.shared.recruits(search: search, stage: stage).items
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct RecruitRow: View {
    let recruit: RecruitOut

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(recruit.fullName).font(.body.weight(.semibold))
                Text(recruit.currentSchool).font(.caption).foregroundStyle(.secondary)
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
    @State private var deleting = false

    var body: some View {
        Group {
            if let r = recruit {
                Form {
                    Section {
                        LabeledRow("Name", r.fullName)
                        HStack {
                            Text("Stage").foregroundStyle(.secondary)
                            Spacer()
                            Menu {
                                ForEach(RecruitStage.allCases) { stage in
                                    Button(stage.label) {
                                        Task { await changeStage(to: stage) }
                                    }
                                }
                            } label: {
                                StageBadge(stage: r.stageValue)
                            }
                        }
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
            Button("Delete", role: .destructive) {
                Task { await deleteRecruit() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This action cannot be undone.")
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

    private func changeStage(to newStage: RecruitStage) async {
        guard let current = recruit, current.stageValue != newStage else { return }
        do {
            recruit = try await APIClient.shared.changeRecruitStage(id: recruitId, toStage: newStage.rawValue)
            history = (try? await APIClient.shared.recruitStageHistory(id: recruitId)) ?? []
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
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
                    stage: "lead",
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
