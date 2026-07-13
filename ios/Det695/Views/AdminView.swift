import SwiftUI

/// Admin console, mirroring the web Admin page (web/src/pages/Admin.tsx): a Users
/// panel (search, add-user sheet, inline role picker + active toggle, delete with
/// confirmation and self-protection) and a reverse-chronological activity log with
/// "Load more". The whole screen is admin-gated — `MoreView` only routes here when
/// the signed-in user is an admin, and a defensive notice covers the rest.
struct AdminView: View {
    @EnvironmentObject private var session: Session

    var body: some View {
        Group {
            if session.user?.isAdmin == true {
                AdminConsole(currentUserId: session.user?.id ?? -1)
            } else {
                restricted
            }
        }
        .navigationTitle("Admin")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var restricted: some View {
        ContentUnavailableView {
            Label("Admins only", systemImage: "lock.fill")
        } description: {
            Text("This area is limited to detachment administrators. Ask an admin if you need access to manage accounts or review the activity log.")
        }
    }
}

private struct AdminConsole: View {
    let currentUserId: Int

    private enum Tab: String, CaseIterable { case users, activity
        var label: String { rawValue.capitalized }
    }

    @State private var tab: Tab = .users
    @State private var search = ""

    var body: some View {
        VStack(spacing: 0) {
            Picker("Section", selection: $tab) {
                ForEach(Tab.allCases, id: \.self) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding([.horizontal, .top])

            switch tab {
            case .users: UsersPanel(currentUserId: currentUserId, search: search)
            case .activity: ActivityPanel()
            }
        }
        .searchable(text: $search, prompt: "Search users")
        // Search only applies to the Users tab; hide the bar's effect on Activity
        // by simply ignoring the text there (the panel doesn't read it).
    }
}

// MARK: - Users

private struct UsersPanel: View {
    let currentUserId: Int
    let search: String

    @State private var users: [UserOut] = []
    @State private var error: String?
    @State private var loading = false
    @State private var adding = false
    @State private var pendingDelete: UserOut?

    var body: some View {
        List {
            if let error { Text(error).foregroundStyle(Theme.danger) }
            ForEach(users) { user in
                UserRow(user: user, isSelf: user.id == currentUserId) { await load() }
                    .swipeActions(edge: .trailing) {
                        if user.id != currentUserId {
                            Button(role: .destructive) { pendingDelete = user } label: {
                                Label("Remove", systemImage: "trash")
                            }
                        }
                    }
            }
            if users.isEmpty && !loading && error == nil {
                ContentUnavailableView(search.isEmpty ? "No users yet" : "No matches",
                                       systemImage: "person.2",
                                       description: Text(search.isEmpty
                                            ? "Add an account so a teammate can sign in."
                                            : "No users match this search."))
            }
            if !users.isEmpty {
                Text("\(users.count) user\(users.count == 1 ? "" : "s")")
                    .font(.caption).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .overlay { if loading && users.isEmpty { ProgressView() } }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { adding = true } label: { Label("Add user", systemImage: "plus") }
            }
        }
        .task(id: search) { await load() }
        .refreshable { await load() }
        .sheet(isPresented: $adding) { AddUserSheet { await load() } }
        .confirmationDialog("Remove this user?",
                            isPresented: Binding(get: { pendingDelete != nil },
                                                 set: { if !$0 { pendingDelete = nil } }),
                            titleVisibility: .visible,
                            presenting: pendingDelete) { user in
            Button("Remove \(user.fullName)", role: .destructive) { Task { await delete(user) } }
            Button("Cancel", role: .cancel) { pendingDelete = nil }
        } message: { _ in Text("They'll lose access immediately. This can't be undone.") }
    }

    private func delete(_ user: UserOut) async {
        pendingDelete = nil
        do {
            try await APIClient.shared.deleteAdminUser(id: user.id)
            await load()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do { users = try await APIClient.shared.adminUsers(search: search).items }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }
}

/// One user: name/username/email, a role menu, and an active/inactive toggle.
/// Both edits patch inline and re-load. A user can't deactivate their own account.
private struct UserRow: View {
    let user: UserOut
    let isSelf: Bool
    let onChange: () async -> Void

    @State private var busy = false
    @State private var error: String?

    private static let roles = ["admin", "recruiter", "viewer"]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(user.fullName).font(.body.weight(.semibold))
                        if isSelf {
                            Text("You").font(.caption2.weight(.semibold))
                                .padding(.horizontal, 6).padding(.vertical, 1)
                                .background(Capsule().fill(Theme.accent.opacity(0.2)))
                        }
                    }
                    Text("@\(user.username)\(user.email.isEmpty ? "" : " · \(user.email)")")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                if busy { ProgressView() }
            }
            HStack(spacing: 12) {
                Menu {
                    ForEach(Self.roles, id: \.self) { r in
                        Button {
                            Task { await update(.init(role: r)) }
                        } label: {
                            if r == user.role { Label(Self.roleLabel(r), systemImage: "checkmark") }
                            else { Text(Self.roleLabel(r)) }
                        }
                    }
                } label: {
                    Label(Self.roleLabel(user.role), systemImage: "person.badge.key")
                        .font(.caption.weight(.medium))
                }
                .disabled(busy)

                Button {
                    Task { await update(.init(isActive: !user.isActive)) }
                } label: {
                    Label(user.isActive ? "Active" : "Inactive",
                          systemImage: user.isActive ? "checkmark.circle.fill" : "slash.circle")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(user.isActive ? Theme.ok : Theme.danger)
                }
                .buttonStyle(.plain)
                .disabled(busy || isSelf)
                Spacer()
            }
            if let error { Text(error).font(.caption).foregroundStyle(Theme.danger) }
        }
        .padding(.vertical, 4)
    }

    private func update(_ body: AdminUserUpdate) async {
        busy = true; error = nil
        defer { busy = false }
        do {
            _ = try await APIClient.shared.updateAdminUser(id: user.id, body)
            await onChange()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    static func roleLabel(_ role: String) -> String {
        switch role {
        case "admin": return "Admin"
        case "recruiter": return "Recruiter"
        case "viewer": return "Viewer (read-only)"
        default: return role.capitalized
        }
    }
}

/// Create-user sheet, mirroring the web add-user drawer: name, username, email,
/// phone, temporary password, role, and a security question/answer pair.
private struct AddUserSheet: View {
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var username = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var password = ""
    @State private var role = "recruiter"
    @State private var secretQuestion = ""
    @State private var secretAnswer = ""
    @State private var saving = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                if let error { Section { Text(error).foregroundStyle(Theme.danger) } }
                Section("Name") {
                    TextField("First name", text: $firstName).textContentType(.givenName)
                    TextField("Last name", text: $lastName).textContentType(.familyName)
                }
                Section("Account") {
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress).keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("Phone (optional)", text: $phone)
                        .textContentType(.telephoneNumber).keyboardType(.phonePad)
                    SecureField("Temporary password", text: $password).textContentType(.newPassword)
                    Picker("Role", selection: $role) {
                        Text("Admin").tag("admin")
                        Text("Recruiter").tag("recruiter")
                        Text("Viewer (read-only)").tag("viewer")
                    }
                }
                Section {
                    TextField("Security question", text: $secretQuestion)
                    TextField("Security answer", text: $secretAnswer)
                } header: {
                    Text("Account recovery")
                } footer: {
                    Text("Used if they need to reset their password. They'll be asked to change the temporary password at first sign-in.")
                }
            }
            .navigationTitle("Add user")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") { Task { await save() } }.disabled(saving || !isValid)
                }
            }
        }
    }

    private var isValid: Bool {
        ![firstName, lastName, username, email, password, secretQuestion, secretAnswer]
            .contains { $0.trimmingCharacters(in: .whitespaces).isEmpty }
    }

    private func save() async {
        saving = true; error = nil
        defer { saving = false }
        let body = AdminUserCreate(
            username: username.trimmingCharacters(in: .whitespaces),
            email: email.trimmingCharacters(in: .whitespaces),
            password: password,
            firstName: firstName.trimmingCharacters(in: .whitespaces),
            lastName: lastName.trimmingCharacters(in: .whitespaces),
            phone: phone.trimmingCharacters(in: .whitespaces).nilIfEmpty,
            role: role,
            secretQuestion: secretQuestion.trimmingCharacters(in: .whitespaces),
            secretAnswer: secretAnswer.trimmingCharacters(in: .whitespaces))
        do {
            _ = try await APIClient.shared.createAdminUser(body)
            dismiss()
            await onSave()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

// MARK: - Activity log

private struct ActivityPanel: View {
    private static let pageSize = 25

    @State private var items: [ActivityLogOut] = []
    @State private var total = 0
    @State private var limit = ActivityPanel.pageSize
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        List {
            if let error { Text(error).foregroundStyle(Theme.danger) }
            ForEach(items) { ev in ActivityRow(event: ev) }
            if items.isEmpty && !loading && error == nil {
                ContentUnavailableView("No activity yet", systemImage: "clock.arrow.circlepath",
                                       description: Text("Actions the team takes will show up here."))
            }
            if !items.isEmpty {
                HStack {
                    Spacer()
                    if items.count < total {
                        Button(loading ? "Loading…" : "Load more") {
                            limit += Self.pageSize
                        }.disabled(loading)
                    } else {
                        Text("Showing all \(total)").font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .overlay { if loading && items.isEmpty { ProgressView() } }
        .task(id: limit) { await load() }
        .refreshable { await load() }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            let page = try await APIClient.shared.adminActivity(skip: 0, limit: limit)
            items = page.items
            total = page.total
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

private struct ActivityRow: View {
    let event: ActivityLogOut

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(event.action).font(.body.weight(.semibold))
            if let d = event.details, !d.isEmpty {
                Text(d).font(.caption).foregroundStyle(.secondary)
            }
            HStack(spacing: 6) {
                if let record = recordLabel {
                    Text(record).font(.caption2).foregroundStyle(.secondary)
                    Text("·").foregroundStyle(.secondary)
                }
                Text("@\(event.username)").font(.caption2).foregroundStyle(.secondary)
                Spacer()
                Text(DateDisplay.mediumDateTime(event.createdAt))
                    .font(.caption2).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }

    private var recordLabel: String? {
        if let desc = event.recordDescription, !desc.isEmpty { return desc }
        if let table = event.tableName, !table.isEmpty {
            if let rid = event.recordId { return "\(table) #\(rid)" }
            return table
        }
        return nil
    }
}
