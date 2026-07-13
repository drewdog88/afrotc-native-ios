import SwiftUI
import UIKit
import UniformTypeIdentifiers

/// Recruiting collateral, mirroring the web Materials page: a segmented control
/// switches between uploaded Documents (download → share, upload, delete) and
/// external Links (open, create, edit, delete). Search filters the active tab.
/// Write actions (upload / add / edit / delete) are gated to non-viewer roles,
/// matching the web's `canWrite`.
struct MaterialsView: View {
    private enum Tab: String, CaseIterable { case documents, links
        var label: String { rawValue.capitalized }
    }

    @EnvironmentObject private var session: Session
    @State private var tab: Tab = .documents
    @State private var search = ""

    private var canWrite: Bool { (session.user?.role ?? "viewer") != "viewer" }

    var body: some View {
        VStack(spacing: 0) {
            Picker("Kind", selection: $tab) {
                ForEach(Tab.allCases, id: \.self) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding()

            switch tab {
            case .documents: DocumentsPanel(search: search, canWrite: canWrite)
            case .links: LinksPanel(search: search, canWrite: canWrite)
            }
        }
        .navigationTitle("Materials")
        .searchable(text: $search, prompt: "Search \(tab.label.lowercased())")
    }
}

// MARK: - Documents

private struct DocumentsPanel: View {
    let search: String
    let canWrite: Bool

    @State private var documents: [DocumentOut] = []
    @State private var error: String?
    @State private var loading = false
    @State private var downloading: Set<Int> = []
    @State private var shareURL: URL?
    @State private var importing = false
    @State private var pendingDelete: DocumentOut?
    @State private var uploadStatus: String?

    var body: some View {
        List {
            if let error { Text(error).foregroundStyle(Theme.danger) }
            if let uploadStatus {
                Label(uploadStatus, systemImage: "checkmark.circle.fill")
                    .font(.footnote).foregroundStyle(Theme.ok)
            }
            ForEach(documents) { doc in
                Button { Task { await download(doc) } } label: { row(doc) }
                    .buttonStyle(.plain)
                    .swipeActions(edge: .trailing) {
                        if canWrite {
                            Button(role: .destructive) { pendingDelete = doc } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
            }
            if documents.isEmpty && !loading && error == nil {
                ContentUnavailableView(search.isEmpty ? "No documents yet" : "No matches",
                                       systemImage: "doc",
                                       description: Text(search.isEmpty
                                            ? "Upload a flyer, checklist, or form to share it with your team."
                                            : "No documents match this search."))
            }
            if !documents.isEmpty {
                Text("\(documents.count) document\(documents.count == 1 ? "" : "s")")
                    .font(.caption).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .overlay { if loading && documents.isEmpty { ProgressView() } }
        .toolbar {
            if canWrite {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { importing = true } label: { Label("Add document", systemImage: "plus") }
                }
            }
        }
        .task(id: search) { await load() }
        .refreshable { await load() }
        .sheet(item: $shareURL) { ActivityView(url: $0) }
        .fileImporter(isPresented: $importing,
                      allowedContentTypes: [.item],
                      allowsMultipleSelection: false) { result in
            Task { await handleImport(result) }
        }
        .confirmationDialog("Delete this document?",
                            isPresented: Binding(get: { pendingDelete != nil },
                                                 set: { if !$0 { pendingDelete = nil } }),
                            titleVisibility: .visible,
                            presenting: pendingDelete) { doc in
            Button("Delete \"\(doc.title)\"", role: .destructive) { Task { await delete(doc) } }
            Button("Cancel", role: .cancel) { pendingDelete = nil }
        } message: { _ in Text("This can't be undone.") }
    }

    private func row(_ doc: DocumentOut) -> some View {
        HStack(spacing: 12) {
            Image(systemName: downloading.contains(doc.id) ? "arrow.down.circle" : "doc.fill")
                .foregroundStyle(Theme.ink)
            VStack(alignment: .leading, spacing: 2) {
                Text(doc.title).font(.body.weight(.semibold))
                Text("\(doc.originalFilename) · \(doc.sizeLabel)")
                    .font(.caption).foregroundStyle(.secondary)
                if let d = doc.description, !d.isEmpty {
                    Text(d).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                }
            }
            Spacer()
            if downloading.contains(doc.id) { ProgressView() }
            else { Image(systemName: "square.and.arrow.up").foregroundStyle(.secondary) }
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }

    private func download(_ doc: DocumentOut) async {
        guard !downloading.contains(doc.id) else { return }
        downloading.insert(doc.id)
        defer { downloading.remove(doc.id) }
        do {
            let data = try await APIClient.shared.downloadDocument(id: doc.id)
            let url = FileManager.default.temporaryDirectory.appendingPathComponent(doc.originalFilename)
            try data.write(to: url, options: .atomic)
            shareURL = url
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func handleImport(_ result: Result<[URL], Error>) async {
        error = nil; uploadStatus = nil
        do {
            guard let url = try result.get().first else { return }
            // Security-scoped resource for files outside the app sandbox.
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            let data = try Data(contentsOf: url)
            let filename = url.lastPathComponent
            let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType
                ?? "application/octet-stream"
            let title = url.deletingPathExtension().lastPathComponent
            _ = try await APIClient.shared.uploadDocument(fileData: data, filename: filename,
                                                          mimeType: mime, title: title)
            uploadStatus = "Uploaded \(filename)."
            await load()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func delete(_ doc: DocumentOut) async {
        pendingDelete = nil
        do {
            try await APIClient.shared.deleteDocument(id: doc.id)
            await load()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do { documents = try await APIClient.shared.materialDocuments(search: search).items }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }
}

// MARK: - Links

private struct LinksPanel: View {
    let search: String
    let canWrite: Bool

    @State private var links: [LinkOut] = []
    @State private var error: String?
    @State private var loading = false
    @State private var editing: LinkOut?
    @State private var adding = false
    @State private var pendingDelete: LinkOut?

    var body: some View {
        List {
            if let error { Text(error).foregroundStyle(Theme.danger) }
            ForEach(links) { link in
                row(link)
                    .swipeActions(edge: .trailing) {
                        if canWrite {
                            Button(role: .destructive) { pendingDelete = link } label: {
                                Label("Delete", systemImage: "trash")
                            }
                            Button { editing = link } label: { Label("Edit", systemImage: "pencil") }
                                .tint(Theme.accent)
                        }
                    }
            }
            if links.isEmpty && !loading && error == nil {
                ContentUnavailableView(search.isEmpty ? "No links yet" : "No matches",
                                       systemImage: "link",
                                       description: Text(search.isEmpty
                                            ? "Add an application portal or scholarship page to keep it handy."
                                            : "No links match this search."))
            }
            if !links.isEmpty {
                Text("\(links.count) link\(links.count == 1 ? "" : "s")")
                    .font(.caption).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .overlay { if loading && links.isEmpty { ProgressView() } }
        .toolbar {
            if canWrite {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { adding = true } label: { Label("Add link", systemImage: "plus") }
                }
            }
        }
        .task(id: search) { await load() }
        .refreshable { await load() }
        .sheet(isPresented: $adding) {
            LinkEditSheet(mode: .create) { await load() }
        }
        .sheet(item: $editing) { link in
            LinkEditSheet(mode: .edit(link)) { await load() }
        }
        .confirmationDialog("Delete this link?",
                            isPresented: Binding(get: { pendingDelete != nil },
                                                 set: { if !$0 { pendingDelete = nil } }),
                            titleVisibility: .visible,
                            presenting: pendingDelete) { link in
            Button("Delete \"\(link.title)\"", role: .destructive) { Task { await delete(link) } }
            Button("Cancel", role: .cancel) { pendingDelete = nil }
        }
    }

    private func row(_ link: LinkOut) -> some View {
        let content = HStack(spacing: 12) {
            Image(systemName: "link").foregroundStyle(Theme.ink)
            VStack(alignment: .leading, spacing: 2) {
                Text(link.title).font(.body.weight(.semibold))
                if let d = link.description, !d.isEmpty {
                    Text(d).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                }
                Text(link.host).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "arrow.up.right.square").foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())

        return Group {
            if let url = URL(string: link.url) {
                Link(destination: url) { content }
            } else {
                content
            }
        }
    }

    private func delete(_ link: LinkOut) async {
        pendingDelete = nil
        do {
            try await APIClient.shared.deleteLink(id: link.id)
            await load()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do { links = try await APIClient.shared.materialLinks(search: search).items }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }
}

/// Shared sheet for creating or editing an external link (title + URL required,
/// category + description optional), mirroring the web LinkDrawer.
private struct LinkEditSheet: View {
    enum Mode { case create, edit(LinkOut) }

    let mode: Mode
    let onSave: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var url = ""
    @State private var category = "general"
    @State private var description = ""
    @State private var saving = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                if let error {
                    Section { Text(error).foregroundStyle(Theme.danger) }
                }
                Section("Required") {
                    TextField("Title", text: $title)
                    TextField("https://…", text: $url)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
                Section("Optional") {
                    TextField("Category", text: $category)
                    TextField("Description", text: $description, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle(isCreate ? "Add link" : "Edit link")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }.disabled(saving || !isValid)
                }
            }
            .onAppear {
                if case let .edit(link) = mode {
                    title = link.title
                    url = link.url
                    category = link.category
                    description = link.description ?? ""
                }
            }
        }
    }

    private var isCreate: Bool { if case .create = mode { return true }; return false }
    private var isValid: Bool {
        !title.trimmingCharacters(in: .whitespaces).isEmpty &&
        !url.trimmingCharacters(in: .whitespaces).isEmpty
    }

    private func save() async {
        saving = true; error = nil
        defer { saving = false }
        let t = title.trimmingCharacters(in: .whitespaces)
        let u = url.trimmingCharacters(in: .whitespaces)
        let cat = category.trimmingCharacters(in: .whitespaces).nilIfEmpty ?? "general"
        let desc = description.trimmingCharacters(in: .whitespaces).nilIfEmpty
        do {
            switch mode {
            case .create:
                _ = try await APIClient.shared.createLink(
                    LinkCreateInput(title: t, url: u, description: desc, category: cat))
            case .edit(let link):
                _ = try await APIClient.shared.updateLink(id: link.id,
                    LinkUpdateInput(title: t, url: u, description: desc, category: cat))
            }
            dismiss()
            await onSave()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// UIActivityViewController wrapper so a downloaded document can be shared/saved.
private struct ActivityView: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: [url], applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}

/// Lets a bare `URL` drive `.sheet(item:)`.
extension URL: Identifiable { public var id: String { absoluteString } }
