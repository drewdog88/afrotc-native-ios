import SwiftUI
import UIKit

/// Recruiting collateral, mirroring the web Materials page: a segmented control
/// switches between uploaded Documents (download → share) and external Links
/// (open in browser). Search filters the active tab.
struct MaterialsView: View {
    private enum Tab: String, CaseIterable { case documents, links
        var label: String { rawValue.capitalized }
    }

    @State private var tab: Tab = .documents
    @State private var search = ""

    var body: some View {
        VStack(spacing: 0) {
            Picker("Kind", selection: $tab) {
                ForEach(Tab.allCases, id: \.self) { Text($0.label).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding()

            switch tab {
            case .documents: DocumentsPanel(search: search)
            case .links: LinksPanel(search: search)
            }
        }
        .navigationTitle("Materials")
        .searchable(text: $search, prompt: "Search \(tab.label.lowercased())")
    }
}

private struct DocumentsPanel: View {
    let search: String
    @State private var documents: [DocumentOut] = []
    @State private var error: String?
    @State private var loading = false
    @State private var downloading: Set<Int> = []
    @State private var shareURL: URL?

    var body: some View {
        List {
            if let error { Text(error).foregroundStyle(Theme.danger) }
            ForEach(documents) { doc in
                Button { Task { await download(doc) } } label: { row(doc) }
                    .buttonStyle(.plain)
            }
            if documents.isEmpty && !loading && error == nil {
                ContentUnavailableView("No documents", systemImage: "doc")
            }
        }
        .listStyle(.plain)
        .overlay { if loading && documents.isEmpty { ProgressView() } }
        .task(id: search) { await load() }
        .refreshable { await load() }
        .sheet(item: $shareURL) { ActivityView(url: $0) }
    }

    private func row(_ doc: DocumentOut) -> some View {
        HStack(spacing: 12) {
            Image(systemName: downloading.contains(doc.id) ? "arrow.down.circle" : "doc.fill")
                .foregroundStyle(Theme.ink)
            VStack(alignment: .leading, spacing: 2) {
                Text(doc.title).font(.body.weight(.semibold))
                Text("\(doc.originalFilename) · \(doc.sizeLabel)")
                    .font(.caption).foregroundStyle(.secondary)
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

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do { documents = try await APIClient.shared.materialDocuments(search: search).items }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }
}

private struct LinksPanel: View {
    let search: String
    @State private var links: [LinkOut] = []
    @State private var error: String?
    @State private var loading = false

    var body: some View {
        List {
            if let error { Text(error).foregroundStyle(Theme.danger) }
            ForEach(links) { link in
                if let url = URL(string: link.url) {
                    Link(destination: url) { row(link) }
                } else {
                    row(link)
                }
            }
            if links.isEmpty && !loading && error == nil {
                ContentUnavailableView("No links", systemImage: "link")
            }
        }
        .listStyle(.plain)
        .overlay { if loading && links.isEmpty { ProgressView() } }
        .task(id: search) { await load() }
        .refreshable { await load() }
    }

    private func row(_ link: LinkOut) -> some View {
        HStack(spacing: 12) {
            Image(systemName: "link").foregroundStyle(Theme.ink)
            VStack(alignment: .leading, spacing: 2) {
                Text(link.title).font(.body.weight(.semibold))
                Text(link.host).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "arrow.up.right.square").foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do { links = try await APIClient.shared.materialLinks(search: search).items }
        catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
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
