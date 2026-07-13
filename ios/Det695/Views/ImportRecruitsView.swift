import SwiftUI
import UniformTypeIdentifiers

/// Bulk recruit import, mirroring the web ImportRecruits wizard. Three steps:
///   1 (upload): pick a CSV/Excel file, see the expected columns.
///   2 (review): submit to /recruits/import, show the per-row result.
///   3 (done):  a summary with imported/skipped/total counts.
/// Presented as a sheet from `RecruitsView`; write-gated to non-viewer roles.
struct ImportRecruitsView: View {
    @Environment(\.dismiss) private var dismiss
    /// Called after a run that imported at least one recruit, so the caller can reload.
    var onImported: () -> Void = {}

    private enum Step: Int { case upload, review, done }

    @State private var step: Step = .upload
    @State private var picking = false
    @State private var fileName: String?
    @State private var fileData: Data?
    @State private var fileMime = "text/csv"
    @State private var pickError: String?
    @State private var error: String?
    @State private var busy = false
    @State private var result: ImportResult?

    private static let expectedColumns = [
        "first_name", "last_name", "email", "phone",
        "current_school", "school_type", "stage",
    ]

    var body: some View {
        NavigationStack {
            Form {
                stepper
                switch step {
                case .upload: uploadStep
                case .review: reviewStep
                case .done: doneStep
                }
            }
            .navigationTitle("Import recruits")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(step == .done ? "Done" : "Cancel") { finish() }
                }
            }
            .fileImporter(isPresented: $picking,
                          allowedContentTypes: importTypes,
                          allowsMultipleSelection: false) { pick($0) }
        }
    }

    private var importTypes: [UTType] {
        [.commaSeparatedText, .spreadsheet, UTType(filenameExtension: "xlsx"),
         UTType(filenameExtension: "xls")].compactMap { $0 }
    }

    // MARK: Stepper

    private var stepper: some View {
        Section {
            HStack(spacing: 8) {
                ForEach([Step.upload, .review, .done], id: \.rawValue) { s in
                    let state = stepState(s)
                    HStack(spacing: 6) {
                        ZStack {
                            Circle()
                                .fill(state == .upcoming ? Color(.systemGray4) : Theme.accent)
                                .frame(width: 22, height: 22)
                            if state == .done {
                                Image(systemName: "checkmark").font(.caption2.bold())
                                    .foregroundStyle(.white)
                            } else {
                                Text("\(s.rawValue + 1)").font(.caption2.bold())
                                    .foregroundStyle(state == .active ? .white : .secondary)
                            }
                        }
                        Text(label(s))
                            .font(.caption.weight(state == .active ? .semibold : .regular))
                            .foregroundStyle(state == .upcoming ? .secondary : .primary)
                    }
                    if s != .done { Spacer(minLength: 0) }
                }
            }
        }
    }

    private enum StepState { case done, active, upcoming }
    private func stepState(_ s: Step) -> StepState {
        if s.rawValue < step.rawValue { return .done }
        if s == step { return .active }
        return .upcoming
    }
    private func label(_ s: Step) -> String {
        switch s { case .upload: "Upload"; case .review: "Review"; case .done: "Done" }
    }

    // MARK: Step 1 — upload

    private var uploadStep: some View {
        Group {
            Section {
                Button { picking = true } label: {
                    HStack(spacing: 12) {
                        Image(systemName: "arrow.up.doc.fill")
                            .font(.title2).foregroundStyle(Theme.accent)
                        VStack(alignment: .leading, spacing: 2) {
                            if let fileName {
                                Text(fileName).font(.body.weight(.semibold))
                                    .foregroundStyle(.primary)
                                if let count = fileData?.count {
                                    Text(byteLabel(count)).font(.caption).foregroundStyle(.secondary)
                                }
                            } else {
                                Text("Choose a file").font(.body.weight(.semibold))
                                    .foregroundStyle(.primary)
                                Text("CSV or Excel (.csv, .xlsx, .xls)")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        if fileName != nil {
                            Image(systemName: "arrow.triangle.2.circlepath").foregroundStyle(.secondary)
                        }
                    }
                }
                if let pickError {
                    Text(pickError).font(.footnote).foregroundStyle(Theme.danger)
                }
            } footer: {
                Text("The first row should be a header. Extra columns are ignored; email and phone can be blank.")
            }

            Section("Expected columns") {
                FlowColumns(items: Self.expectedColumns)
            }

            Section {
                Button { submit() } label: {
                    Text("Import file").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.accent)
                .disabled(fileData == nil)
            }
        }
    }

    // MARK: Step 2 — review

    private var reviewStep: some View {
        Group {
            if busy {
                Section {
                    HStack(spacing: 12) {
                        ProgressView()
                        Text("Reading your file and creating recruits…")
                            .foregroundStyle(.secondary)
                    }
                }
            } else if let error {
                Section {
                    Text(error).foregroundStyle(Theme.danger)
                    Button("Back") { self.error = nil; step = .upload }
                    Button("Try again") { submit() }
                }
            } else if let result {
                summary(result)
                if result.errors.isEmpty {
                    Section {
                        Label("Every row imported cleanly. Nice work.",
                              systemImage: "checkmark.seal.fill")
                            .foregroundStyle(Theme.ok)
                    }
                } else {
                    Section {
                        ForEach(result.errors) { rowErr in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Row \(rowErr.row)")
                                    .font(.caption.weight(.semibold)).foregroundStyle(Theme.danger)
                                ForEach(Array(rowErr.errors.enumerated()), id: \.offset) { _, m in
                                    Text("• \(m)").font(.footnote).foregroundStyle(.secondary)
                                }
                            }
                            .padding(.vertical, 2)
                        }
                    } header: {
                        Text("Rows that need a fix")
                    } footer: {
                        Text("Fix these rows in your spreadsheet and import again — imported rows won't be duplicated if they already exist.")
                    }
                }
                Section {
                    Button("Import another file") { reset() }
                    Button { step = .done } label: {
                        Text("Continue").frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(Theme.accent)
                }
            }
        }
    }

    // MARK: Step 3 — done

    private var doneStep: some View {
        Group {
            if let result {
                Section {
                    let clean = result.failed == 0
                    Label(clean ? "Import complete" : "Import finished with some skipped rows",
                          systemImage: clean ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                        .font(.headline)
                        .foregroundStyle(clean ? Theme.ok : Theme.accent)
                    Text(doneCopy(result)).foregroundStyle(.secondary)
                }
                summary(result)
                Section {
                    Button("Import another file") { reset() }
                    Button { finish() } label: {
                        Text("Done").frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(Theme.accent)
                }
            }
        }
    }

    private func doneCopy(_ r: ImportResult) -> String {
        var s = r.imported == 0
            ? "No new recruits were added."
            : "Added \(r.imported) recruit\(r.imported == 1 ? "" : "s") to your pipeline."
        if r.failed > 0 {
            s += " \(r.failed) row\(r.failed == 1 ? "" : "s") were skipped."
        }
        return s
    }

    // MARK: Shared summary

    private func summary(_ r: ImportResult) -> some View {
        Section {
            HStack {
                stat("Imported", r.imported, tint: Theme.ok)
                Divider()
                stat("Skipped", r.failed, tint: r.failed > 0 ? Theme.danger : .secondary)
                Divider()
                stat("Total rows", r.totalRows, tint: .primary)
            }
            .frame(maxWidth: .infinity)
        }
    }

    private func stat(_ label: String, _ value: Int, tint: Color) -> some View {
        VStack(spacing: 2) {
            Text("\(value)").font(.title2.weight(.bold).monospacedDigit()).foregroundStyle(tint)
            Text(label).font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: Actions

    private func pick(_ res: Result<[URL], Error>) {
        pickError = nil
        do {
            guard let url = try res.get().first else { return }
            let ext = url.pathExtension.lowercased()
            guard ["csv", "xlsx", "xls"].contains(ext) else {
                pickError = "Choose a .csv or .xlsx file."
                return
            }
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            fileData = try Data(contentsOf: url)
            fileName = url.lastPathComponent
            fileMime = UTType(filenameExtension: ext)?.preferredMIMEType ?? "text/csv"
        } catch {
            pickError = "Couldn't read that file. Try choosing it again."
        }
    }

    private func submit() {
        guard let data = fileData, let name = fileName else { return }
        error = nil
        busy = true
        step = .review
        Task {
            defer { busy = false }
            do {
                let res = try await APIClient.shared.importRecruits(
                    fileData: data, filename: name, mimeType: fileMime)
                result = res
                if res.imported > 0 { onImported() }
            } catch {
                self.error = (error as? APIError)?.errorDescription
                    ?? "Couldn't import that file. Check the format and try again."
            }
        }
    }

    private func reset() {
        fileData = nil
        fileName = nil
        pickError = nil
        error = nil
        result = nil
        step = .upload
    }

    private func finish() { dismiss() }

    private func byteLabel(_ bytes: Int) -> String {
        if bytes < 1024 { return "\(bytes) B" }
        if bytes < 1024 * 1024 { return String(format: "%.1f KB", Double(bytes) / 1024) }
        return String(format: "%.1f MB", Double(bytes) / (1024 * 1024))
    }
}

/// A simple wrapping row of monospaced column-name chips for the expected-columns hint.
private struct FlowColumns: View {
    let items: [String]

    var body: some View {
        // Two-per-row grid keeps it tidy in a Form without a full flow layout.
        let rows = stride(from: 0, to: items.count, by: 2).map {
            Array(items[$0..<min($0 + 2, items.count)])
        }
        VStack(alignment: .leading, spacing: 6) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, pair in
                HStack(spacing: 8) {
                    ForEach(pair, id: \.self) { chip($0) }
                    Spacer(minLength: 0)
                }
            }
        }
    }

    private func chip(_ name: String) -> some View {
        Text(name)
            .font(.caption.monospaced())
            .padding(.horizontal, 8).padding(.vertical, 4)
            .background(Color(.systemGray5), in: Capsule())
    }
}
