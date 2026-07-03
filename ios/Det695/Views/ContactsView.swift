import SwiftUI

/// Typed navigation route for a contact detail (kept distinct from other Int
/// routes so several screens can share one NavigationStack in the More tab).
struct ContactRoute: Hashable { let id: Int }

/// University/high-school contacts with search + active filter, mirroring the
/// web Contacts page. Rows push a read-only detail.
struct ContactsView: View {
    @State private var contacts: [ContactOut] = []
    @State private var search = ""
    /// nil = all, true = active only, false = inactive only.
    @State private var activeFilter: Bool?
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        List {
            if let error {
                Text(error).foregroundStyle(Theme.danger)
            }
            ForEach(contacts) { c in
                NavigationLink(value: ContactRoute(id: c.id)) { ContactRow(contact: c) }
            }
            if contacts.isEmpty && !loading && error == nil {
                ContentUnavailableView("No contacts", systemImage: "building.columns")
            }
        }
        .listStyle(.plain)
        .overlay { if loading && contacts.isEmpty { ProgressView() } }
        .navigationTitle("Contacts")
        .navigationDestination(for: ContactRoute.self) { ContactDetailView(contactId: $0.id) }
        .searchable(text: $search, prompt: "Search contacts")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("All") { activeFilter = nil }
                    Button("Active") { activeFilter = true }
                    Button("Inactive") { activeFilter = false }
                } label: {
                    Label(filterLabel, systemImage: "line.3.horizontal.decrease.circle")
                }
            }
        }
        .task(id: filterKey) { await load() }
        .refreshable { await load() }
    }

    private var filterLabel: String {
        switch activeFilter { case .some(true): "Active"; case .some(false): "Inactive"; case .none: "All" }
    }
    private var filterKey: String { "\(search)|\(activeFilter.map(String.init) ?? "")" }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            contacts = try await APIClient.shared.contacts(search: search, isActive: activeFilter).items
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
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
                Text(contact.universityName).font(.caption).foregroundStyle(.secondary)
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
                        }
                    }
                    if let n = c.notes, !n.isEmpty {
                        Section("Notes") { Text(n) }
                    }
                    Section {
                        LabeledRow("Added", DateDisplay.mediumDate(c.createdAt))
                        LabeledRow("Updated", DateDisplay.mediumDate(c.lastModified))
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
        .task { await load() }
    }

    private func load() async {
        do { contact = try await APIClient.shared.contact(id: contactId) }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
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
