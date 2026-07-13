import SwiftUI

/// Typed navigation route for a contact detail (kept distinct from other Int
/// routes so several screens can share one NavigationStack in the More tab).
struct ContactRoute: Hashable { let id: Int }

/// University/high-school contacts with search + active filter, mirroring the
/// web Contacts page. Rows push a read-only detail.
struct ContactsView: View {
    @State private var contacts: [ContactOut] = []
    @State private var total = 0
    @State private var search = ""
    /// nil = all, true = active only, false = inactive only.
    @State private var activeFilter: Bool?
    @State private var error: String?
    @State private var loading = false
    @State private var showingCreate = false

    var body: some View {
        List {
            Section {
                ContactStatusChips(activeFilter: $activeFilter)
                    .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 4, trailing: 0))
                    .listRowSeparator(.hidden)
            }
            if let error {
                Text(error).foregroundStyle(Theme.danger)
            }
            ForEach(contacts) { c in
                NavigationLink(value: ContactRoute(id: c.id)) { ContactRow(contact: c) }
            }
            if contacts.isEmpty && !loading && error == nil {
                ContentUnavailableView {
                    Label(isFiltered ? "No matches" : "No contacts yet", systemImage: "building.columns")
                } description: {
                    Text(isFiltered
                         ? "No contacts match this view."
                         : "Add your first point of contact to get started.")
                }
                .listRowSeparator(.hidden)
            }
            if !contacts.isEmpty {
                Text(countLabel)
                    .font(.footnote).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .overlay { if loading && contacts.isEmpty { ProgressView() } }
        .navigationTitle("Contacts")
        .navigationDestination(for: ContactRoute.self) { ContactDetailView(contactId: $0.id) }
        .searchable(text: $search, prompt: "Search by name, school, or email")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showingCreate = true } label: {
                    Label("Add", systemImage: "plus")
                }
            }
        }
        .sheet(isPresented: $showingCreate) {
            ContactEditSheet(mode: .create) {
                await load()
            }
        }
        .task(id: filterKey) { await load() }
        .refreshable { await load() }
    }

    private var filterKey: String { "\(search)|\(activeFilter.map(String.init) ?? "")" }
    private var isFiltered: Bool { !search.isEmpty || activeFilter != nil }

    private var countLabel: String {
        let shown = contacts.count
        let suffix = total > shown ? " of \(total)" : ""
        return "\(shown)\(suffix) contact\(total == 1 ? "" : "s")"
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            let page = try await APIClient.shared.contacts(search: search, isActive: activeFilter)
            contacts = page.items
            total = page.total
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Active-status filter chips (All / Active / Inactive), mirroring the web chip row.
private struct ContactStatusChips: View {
    @Binding var activeFilter: Bool?

    private var options: [(label: String, value: Bool?, tint: Color)] {
        [("All", nil, Theme.ink), ("Active", true, Theme.ok), ("Inactive", false, Theme.muted)]
    }

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(options, id: \.label) { opt in
                    let active = activeFilter == opt.value
                    Button {
                        activeFilter = (activeFilter == opt.value && opt.value != nil) ? nil : opt.value
                    } label: {
                        Text(opt.label)
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 12).padding(.vertical, 6)
                            .background(active ? opt.tint : opt.tint.opacity(0.12), in: Capsule())
                            .foregroundStyle(active ? .white : opt.tint)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
        }
    }
}

private struct ContactRow: View {
    let contact: ContactOut

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(contact.isActive ? Theme.ok : Theme.muted)
                .frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text(contact.contactName).font(.body.weight(.semibold))
                if let title = contact.contactTitle, !title.isEmpty {
                    Text("\(title) · \(contact.universityName)")
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Text(contact.universityName).font(.caption).foregroundStyle(.secondary)
                }
                if !contact.email.isEmpty {
                    Text(contact.email).font(.caption2).foregroundStyle(.secondary)
                }
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }
}

/// Read-only contact detail, fetched fresh by id.
struct ContactDetailView: View {
    let contactId: Int
    @State private var contact: ContactOut?
    @State private var error: String?
    @State private var showingEdit = false
    @State private var showingDeleteConfirm = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        Group {
            if let c = contact {
                Form {
                    Section {
                        LabeledRow("Contact", c.contactName)
                        if let t = c.contactTitle, !t.isEmpty { LabeledRow("Title", t) }
                        LabeledRow("School", c.universityName)
                        LabeledRow("Status", c.isActive ? "Active" : "Inactive")
                    }
                    Section("Reach") {
                        LinkRow(label: "Email", value: c.email, url: URL(string: "mailto:\(c.email)"))
                        if let p = c.phone, !p.isEmpty {
                            LinkRow(label: "Phone", value: p,
                                    url: URL(string: "tel:\(p.filter { $0.isNumber || $0 == "+" })"))
                        }
                        if let a = c.address, !a.isEmpty { LabeledRow("Address", a) }
                        if let lat = c.latitude, let lon = c.longitude {
                            LinkRow(label: "Map", value: "Open in Maps",
                                    url: URL(string: "https://maps.apple.com/?q=\(lat),\(lon)"))
                            LabeledRow("Latitude", String(format: "%.5f", lat))
                            LabeledRow("Longitude", String(format: "%.5f", lon))
                        }
                    }
                    if let n = c.notes, !n.isEmpty {
                        Section("Notes") { Text(n) }
                    }
                    Section {
                        LabeledRow("Added", DateDisplay.mediumDate(c.createdAt))
                        LabeledRow("Updated", DateDisplay.mediumDate(c.lastModified))
                    }
                    Section {
                        Button(role: .destructive) {
                            showingDeleteConfirm = true
                        } label: {
                            Label("Delete contact", systemImage: "trash")
                                .frame(maxWidth: .infinity)
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
        .navigationTitle(contact?.contactName ?? "Contact")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if contact != nil {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Edit") { showingEdit = true }
                }
            }
        }
        .sheet(isPresented: $showingEdit) {
            if let c = contact {
                ContactEditSheet(mode: .edit(c)) {
                    await load()
                }
            }
        }
        .confirmationDialog("Delete this contact?", isPresented: $showingDeleteConfirm, titleVisibility: .visible) {
            Button("Delete \(contact?.contactName ?? "contact")", role: .destructive) {
                Task { await deleteContact() }
            }
            Button("Cancel", role: .cancel) { }
        } message: {
            Text("This permanently removes \(contact?.contactName ?? "this contact"). This can't be undone.")
        }
        .task { await load() }
    }

    private func load() async {
        do { contact = try await APIClient.shared.contact(id: contactId) }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }

    private func deleteContact() async {
        do {
            try await APIClient.shared.deleteContact(id: contactId)
            dismiss()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// A left-label / right-value form row.
struct LabeledRow: View {
    let label: String
    let value: String
    init(_ label: String, _ value: String) { self.label = label; self.value = value }
    var body: some View {
        HStack(alignment: .top) {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value).multilineTextAlignment(.trailing)
        }
    }
}

/// A form row whose value is a tappable link (email/phone/map), degrading to
/// plain text when the URL can't be built.
struct LinkRow: View {
    let label: String
    let value: String
    let url: URL?
    var body: some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            if let url { Link(value, destination: url) } else { Text(value) }
        }
    }
}

/// Shared sheet for creating or editing a contact.
struct ContactEditSheet: View {
    enum Mode {
        case create
        case edit(ContactOut)
    }

    let mode: Mode
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var universityName = ""
    @State private var contactName = ""
    @State private var email = ""
    @State private var contactTitle = ""
    @State private var phone = ""
    @State private var address = ""
    @State private var notes = ""
    @State private var isActive = true
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
                    TextField("University/School Name", text: $universityName)
                    TextField("Contact Name", text: $contactName)
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                }

                Section("Optional") {
                    TextField("Contact Title", text: $contactTitle)
                    TextField("Phone", text: $phone)
                        .keyboardType(.phonePad)
                    TextField("Address", text: $address)
                    Toggle("Active", isOn: $isActive)
                }

                Section("Notes") {
                    TextField("Notes", text: $notes, axis: .vertical)
                        .lineLimit(4...8)
                }
            }
            .navigationTitle(mode.isCreate ? "New Contact" : "Edit Contact")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(saving || !isValid)
                }
            }
            .onAppear {
                if case let .edit(contact) = mode {
                    universityName = contact.universityName
                    contactName = contact.contactName
                    email = contact.email
                    contactTitle = contact.contactTitle ?? ""
                    phone = contact.phone ?? ""
                    address = contact.address ?? ""
                    notes = contact.notes ?? ""
                    isActive = contact.isActive
                }
            }
        }
    }

    private var isValid: Bool {
        !universityName.trimmingCharacters(in: .whitespaces).isEmpty &&
        !contactName.trimmingCharacters(in: .whitespaces).isEmpty &&
        !email.trimmingCharacters(in: .whitespaces).isEmpty
    }

    private func save() async {
        saving = true
        error = nil
        defer { saving = false }

        do {
            switch mode {
            case .create:
                let input = ContactCreateInput(
                    universityName: universityName.trimmingCharacters(in: .whitespaces),
                    contactName: contactName.trimmingCharacters(in: .whitespaces),
                    email: email.trimmingCharacters(in: .whitespaces),
                    isActive: isActive,
                    contactTitle: contactTitle.trimmingCharacters(in: .whitespaces).nilIfEmpty,
                    phone: phone.trimmingCharacters(in: .whitespaces).nilIfEmpty,
                    address: address.trimmingCharacters(in: .whitespaces).nilIfEmpty,
                    notes: notes.trimmingCharacters(in: .whitespaces).nilIfEmpty
                )
                _ = try await APIClient.shared.createContact(input)

            case .edit(let contact):
                let input = ContactUpdateInput(
                    universityName: universityName.trimmingCharacters(in: .whitespaces),
                    contactName: contactName.trimmingCharacters(in: .whitespaces),
                    email: email.trimmingCharacters(in: .whitespaces),
                    isActive: isActive,
                    contactTitle: contactTitle.trimmingCharacters(in: .whitespaces).nilIfEmpty,
                    phone: phone.trimmingCharacters(in: .whitespaces).nilIfEmpty,
                    address: address.trimmingCharacters(in: .whitespaces).nilIfEmpty,
                    notes: notes.trimmingCharacters(in: .whitespaces).nilIfEmpty
                )
                _ = try await APIClient.shared.updateContact(id: contact.id, input)
            }

            dismiss()
            await onSave()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

extension ContactEditSheet.Mode {
    var isCreate: Bool {
        if case .create = self { return true }
        return false
    }
}

extension String {
    var nilIfEmpty: String? {
        let trimmed = trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? nil : trimmed
    }
}
