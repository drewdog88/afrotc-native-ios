import SwiftUI

/// Typed navigation route to a cadet detail, distinct from other Int routes.
struct CadetRoute: Hashable { let id: Int }

/// Cadets directory with search + status filter (active / inactive / graduated),
/// mirroring the web Cadets page.
struct CadetsView: View {
    private static let statuses = ["active", "inactive", "graduated"]

    @EnvironmentObject private var router: AppRouter

    @State private var cadets: [CadetOut] = []
    @State private var search = ""
    @State private var status: String?
    @State private var error: String?
    @State private var loading = false
    @State private var showingCreateSheet = false

    var body: some View {
        NavigationStack {
            List {
                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                }
                ForEach(cadets) { c in
                    NavigationLink(value: CadetRoute(id: c.id)) { CadetRow(cadet: c) }
                }
                if cadets.isEmpty && !loading && error == nil {
                    ContentUnavailableView("No cadets", systemImage: "shield")
                }
            }
            .listStyle(.plain)
            .overlay { if loading && cadets.isEmpty { ProgressView() } }
            .navigationTitle("Cadets")
            .navigationBarTitleDisplayMode(.inline)
            .det695BrandBar()
            .navigationDestination(for: CadetRoute.self) { CadetDetailView(cadetId: $0.id) }
            .searchable(text: $search, prompt: "Search cadets")
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
                        ForEach(Self.statuses, id: \.self) { s in
                            Button(s.capitalized) { status = s }
                        }
                    } label: {
                        Label(status?.capitalized ?? "All", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
            .sheet(isPresented: $showingCreateSheet) {
                CadetFormSheet(mode: .create) {
                    await load()
                }
            }
            .task(id: filterKey) { await load() }
            .refreshable { await load() }
            .onAppear { applyPendingStatus() }
            .onChange(of: router.pendingCadetStatus) { oldValue, newValue in
                applyPendingStatus()
            }
        }
    }

    private func applyPendingStatus() {
        guard let pendingStatus = router.pendingCadetStatus else { return }
        status = pendingStatus
        router.pendingCadetStatus = nil
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

/// Read-only cadet detail, fetched fresh by id. Mirrors the web cadet detail:
/// profile fields plus unenrollment info when the cadet is inactive.
struct CadetDetailView: View {
    let cadetId: Int
    @State private var cadet: CadetOut?
    @State private var error: String?
    @State private var showingEditSheet = false
    @State private var showingDeleteConfirm = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        Group {
            if let c = cadet {
                Form {
                    Section {
                        LabeledRow("Name", c.fullName)
                        HStack {
                            Text("Status").foregroundStyle(.secondary)
                            Spacer()
                            Text(c.statusLabel)
                                .foregroundStyle(Theme.cadetStatusColor(c.status))
                        }
                        LabeledRow("Rank", c.cadetRank)
                        LabeledRow("Major", c.major)
                        LabeledRow("Graduation year", String(c.graduationYear))
                        if let g = c.gpa { LabeledRow("GPA", String(format: "%.2f", g)) }
                        if let h = c.hometown, !h.isEmpty { LabeledRow("Hometown", h) }
                    }
                    Section("Reach") {
                        LinkRow(label: "Email", value: c.email, url: URL(string: "mailto:\(c.email)"))
                        if let p = c.phone, !p.isEmpty {
                            LinkRow(label: "Phone", value: p,
                                    url: URL(string: "tel:\(p.filter { $0.isNumber || $0 == "+" })"))
                        }
                    }
                    if let o = c.officerInterest, !o.isEmpty {
                        Section("Officer interest") { Text(o) }
                    }
                    if c.status.lowercased() == "inactive" {
                        Section("Unenrollment") {
                            if let r = c.unenrollmentReason, !r.isEmpty { LabeledRow("Reason", r) }
                            if let d = c.unenrollmentDate, !d.isEmpty {
                                LabeledRow("Date", DateDisplay.mediumDate(d))
                            }
                        }
                    }
                    Section {
                        Button(role: .destructive) {
                            showingDeleteConfirm = true
                        } label: {
                            HStack {
                                Spacer()
                                Text("Delete cadet")
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
        .navigationTitle(cadet?.fullName ?? "Cadet")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit") {
                    showingEditSheet = true
                }
                .disabled(cadet == nil)
            }
        }
        .sheet(isPresented: $showingEditSheet) {
            if let c = cadet {
                CadetFormSheet(mode: .edit(c)) {
                    await load()
                }
            }
        }
        .confirmationDialog("Delete this cadet?", isPresented: $showingDeleteConfirm, titleVisibility: .visible) {
            Button("Delete", role: .destructive) {
                Task { await deleteCadet() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This action cannot be undone.")
        }
        .task { await load() }
    }

    private func load() async {
        do { cadet = try await APIClient.shared.cadet(id: cadetId) }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }

    private func deleteCadet() async {
        do {
            try await APIClient.shared.deleteCadet(id: cadetId)
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Shared form sheet for creating or editing a cadet.
private struct CadetFormSheet: View {
    enum Mode {
        case create
        case edit(CadetOut)
    }

    let mode: Mode
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var email = ""
    @State private var major = ""
    @State private var graduationYear = ""
    @State private var cadetRank = ""
    @State private var status = "active"
    @State private var phone = ""
    @State private var hometown = ""
    @State private var officerInterest = ""
    @State private var gpa = ""
    @State private var unenrollmentReason = ""
    @State private var unenrollmentDate = ""
    @State private var saving = false
    @State private var error: String?

    private let statuses = ["active", "inactive", "graduated"]

    var body: some View {
        NavigationStack {
            Form {
                if let error {
                    Section {
                        Text(error).foregroundStyle(Theme.danger)
                    }
                }

                Section("Required") {
                    TextField("First name", text: $firstName)
                    TextField("Last name", text: $lastName)
                    TextField("Email", text: $email)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.emailAddress)
                    TextField("Major", text: $major)
                    TextField("Graduation year", text: $graduationYear)
                        .keyboardType(.numberPad)
                    TextField("Cadet rank", text: $cadetRank)
                }

                Section("Status") {
                    Picker("Status", selection: $status) {
                        ForEach(statuses, id: \.self) { s in
                            Text(s.capitalized).tag(s)
                        }
                    }
                    .pickerStyle(.segmented)

                    if status == "inactive" {
                        TextField("Unenrollment reason", text: $unenrollmentReason)
                        TextField("Unenrollment date (YYYY-MM-DD)", text: $unenrollmentDate)
                            .textInputAutocapitalization(.never)
                    }
                }

                Section("Optional") {
                    TextField("Phone", text: $phone)
                        .keyboardType(.phonePad)
                    TextField("Hometown", text: $hometown)
                    TextField("Officer interest", text: $officerInterest, axis: .vertical)
                        .lineLimit(3...6)
                    TextField("GPA", text: $gpa)
                        .keyboardType(.decimalPad)
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
        !firstName.isEmpty && !lastName.isEmpty && !email.isEmpty &&
        !major.isEmpty && !graduationYear.isEmpty && !cadetRank.isEmpty &&
        Int(graduationYear) != nil
    }

    private func prefillIfNeeded() {
        guard case .edit(let cadet) = mode else { return }
        firstName = cadet.firstName
        lastName = cadet.lastName
        email = cadet.email
        major = cadet.major
        graduationYear = String(cadet.graduationYear)
        cadetRank = cadet.cadetRank
        status = cadet.status
        phone = cadet.phone ?? ""
        hometown = cadet.hometown ?? ""
        officerInterest = cadet.officerInterest ?? ""
        if let g = cadet.gpa {
            gpa = String(format: "%.2f", g)
        }
        unenrollmentReason = cadet.unenrollmentReason ?? ""
        unenrollmentDate = cadet.unenrollmentDate ?? ""
    }

    private func save() async {
        saving = true
        error = nil
        defer { saving = false }

        do {
            switch mode {
            case .create:
                let input = CadetCreateInput(
                    firstName: firstName,
                    lastName: lastName,
                    email: email,
                    major: major,
                    graduationYear: Int(graduationYear)!,
                    cadetRank: cadetRank,
                    status: status,
                    phone: phone.isEmpty ? nil : phone,
                    hometown: hometown.isEmpty ? nil : hometown,
                    officerInterest: officerInterest.isEmpty ? nil : officerInterest,
                    gpa: Double(gpa)
                )
                _ = try await APIClient.shared.createCadet(input)
            case .edit(let cadet):
                let input = CadetUpdateInput(
                    firstName: firstName,
                    lastName: lastName,
                    email: email,
                    major: major,
                    graduationYear: Int(graduationYear)!,
                    cadetRank: cadetRank,
                    status: status,
                    phone: phone.isEmpty ? nil : phone,
                    hometown: hometown.isEmpty ? nil : hometown,
                    officerInterest: officerInterest.isEmpty ? nil : officerInterest,
                    unenrollmentReason: unenrollmentReason.isEmpty ? nil : unenrollmentReason,
                    unenrollmentDate: unenrollmentDate.isEmpty ? nil : unenrollmentDate,
                    gpa: Double(gpa)
                )
                _ = try await APIClient.shared.updateCadet(id: cadet.id, input)
            }
            await onSave()
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private extension CadetFormSheet.Mode {
    var title: String {
        switch self {
        case .create: return "New Cadet"
        case .edit: return "Edit Cadet"
        }
    }
}
