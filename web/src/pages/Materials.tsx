/* Materials library — the shared shelf of recruiting collateral. Two sections:
   uploaded documents (flyers, checklists, forms) that recruiters can download, and
   external links (application portals, scholarship pages) that open in a new tab.
   Documents are stored through the API as file bytes; links are just titled URLs. */
import { useRef, useState, type FormEvent } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { components } from "../api/schema";
import styles from "./Materials.module.css";

type DocumentOut = components["schemas"]["DocumentOut"];
type DocumentPage = components["schemas"]["Page_DocumentOut_"];
type LinkOut = components["schemas"]["LinkOut"];
type LinkCreate = components["schemas"]["LinkCreate"];
type LinkUpdate = components["schemas"]["LinkUpdate"];
type LinkPage = components["schemas"]["Page_LinkOut_"];

type Tab = "documents" | "links";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function fmtSize(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(kb < 10 ? 1 : 0)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(mb < 10 ? 1 : 0)} MB`;
}

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function Materials() {
  const { canWrite } = useAuth();
  const [tab, setTab] = useState<Tab>("documents");
  const [search, setSearch] = useState("");

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Materials</h1>
          <p className={styles.subtitle}>
            Shared documents and external links your team can hand to prospects.
          </p>
        </div>
      </div>

      <div className={styles.toolbar}>
        <div className={styles.tabs} role="tablist" aria-label="Material type">
          <button
            role="tab"
            aria-selected={tab === "documents"}
            className={`${styles.tab} ${tab === "documents" ? styles.tabActive : ""}`}
            onClick={() => setTab("documents")}
          >
            Documents
          </button>
          <button
            role="tab"
            aria-selected={tab === "links"}
            className={`${styles.tab} ${tab === "links" ? styles.tabActive : ""}`}
            onClick={() => setTab("links")}
          >
            Links
          </button>
        </div>
        <input
          className={`input ${styles.search}`}
          placeholder={tab === "documents" ? "Search documents…" : "Search links…"}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label={tab === "documents" ? "Search documents" : "Search links"}
        />
      </div>

      {tab === "documents" ? (
        <DocumentsPanel search={search.trim()} canWrite={canWrite} />
      ) : (
        <LinksPanel search={search.trim()} canWrite={canWrite} />
      )}
    </div>
  );
}

/* ---------------- Documents ---------------- */

function DocumentsPanel({ search, canWrite }: { search: string; canWrite: boolean }) {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const params = new URLSearchParams({ limit: "200" });
  if (search) params.set("search", search);

  const listQ = useQuery({
    queryKey: ["materials-documents", search],
    queryFn: () => api.get<DocumentPage>(`/materials/documents?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const items = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;

  const del = useMutation({
    mutationFn: (id: number) => api.del(`/materials/documents/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["materials-documents"] }),
  });

  async function download(doc: DocumentOut) {
    setDownloadError(null);
    setDownloadingId(doc.id);
    try {
      const res = await api.raw(`/materials/documents/${doc.id}/download`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename || doc.filename || doc.title;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(err instanceof ApiError ? err.message : "Couldn't download that file.");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <>
      <div className={styles.panelHead}>
        <span className={styles.eyebrow}>Documents</span>
        {canWrite && (
          <button className="btn btn-primary" onClick={() => setUploading(true)}>
            Add document
          </button>
        )}
      </div>

      {downloadError && <div className={styles.formError}>{downloadError}</div>}

      <section className={`card ${styles.tableWrap}`}>
        {listQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 260, margin: "var(--sp-4)" }} />
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            {search
              ? "No documents match this search."
              : "No documents yet. Upload a flyer, checklist, or form to share it with your team."}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Title</th>
                <th className={styles.colHide}>Size</th>
                <th className={styles.colHide}>Uploaded</th>
                <th className={styles.right}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((doc) => (
                <tr key={doc.id} className={styles.staticRow}>
                  <td>
                    <div className={styles.name}>{doc.title}</div>
                    <div className={styles.sub}>{doc.original_filename}</div>
                    {doc.description && <div className={styles.desc}>{doc.description}</div>}
                  </td>
                  <td className={`${styles.colHide} ${styles.mono}`}>{fmtSize(doc.file_size)}</td>
                  <td className={`${styles.colHide} ${styles.mono}`}>{fmtDate(doc.created_at)}</td>
                  <td className={styles.right}>
                    <div className={styles.rowActions}>
                      <button
                        className=”btn btn-ghost”
                        onClick={() => download(doc)}
                        disabled={downloadingId === doc.id}
                      >
                        {downloadingId === doc.id ? “Preparing…” : “Download”}
                      </button>
                      {canWrite && (
                        <button
                          className={`btn btn-ghost ${styles.dangerBtn}`}
                          onClick={() => {
                            if (window.confirm(`Delete “${doc.title}”? This can't be undone.`)) del.mutate(doc.id);
                          }}
                          disabled={del.isPending}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {!listQ.isLoading && items.length > 0 && (
        <div className={styles.count}>
          {items.length}
          {total > items.length ? ` of ${total}` : ""} document{total === 1 ? "" : "s"}
        </div>
      )}

      {uploading && <UploadDrawer onClose={() => setUploading(false)} />}
    </>
  );
}

function UploadDrawer({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (chosen: File) => {
      const form = new FormData();
      form.append("file", chosen);
      const q = new URLSearchParams();
      if (title.trim()) q.set("title", title.trim());
      if (description.trim()) q.set("description", description.trim());
      if (category.trim()) q.set("category", category.trim());
      const qs = q.toString();
      return api.postForm<DocumentOut>(`/materials/documents${qs ? `?${qs}` : ""}`, form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials-documents"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't upload that file."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    upload.mutate(file);
  }

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>Add document</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.field}>
          <label className="field-label" htmlFor="doc_file">File</label>
          <input
            ref={fileRef}
            id="doc_file"
            className={styles.fileInput}
            type="file"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              if (f && !title.trim()) setTitle(f.name.replace(/\.[^.]+$/, ""));
            }}
          />
          {file && <div className={styles.sub}>{file.name} · {fmtSize(file.size)}</div>}
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="doc_title">Title</label>
          <input
            id="doc_title"
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Shown in the library"
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="doc_category">Category</label>
          <input
            id="doc_category"
            className="input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g. flyer, checklist, form"
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="doc_desc">Description</label>
          <textarea
            id="doc_desc"
            className={styles.noteInput}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this document for? (optional)"
          />
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={upload.isPending}>
            {upload.isPending ? "Uploading…" : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ---------------- Links ---------------- */

function LinksPanel({ search, canWrite }: { search: string; canWrite: boolean }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<LinkOut | null>(null);
  const [adding, setAdding] = useState(false);

  const params = new URLSearchParams({ limit: "200" });
  if (search) params.set("search", search);

  const listQ = useQuery({
    queryKey: ["materials-links", search],
    queryFn: () => api.get<LinkPage>(`/materials/links?${params.toString()}`),
    placeholderData: keepPreviousData,
  });

  const items = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;

  const del = useMutation({
    mutationFn: (id: number) => api.del(`/materials/links/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["materials-links"] }),
  });

  return (
    <>
      <div className={styles.panelHead}>
        <span className={styles.eyebrow}>Links</span>
        {canWrite && (
          <button className="btn btn-primary" onClick={() => setAdding(true)}>
            Add link
          </button>
        )}
      </div>

      <section className={`card ${styles.tableWrap}`}>
        {listQ.isLoading ? (
          <div className={styles.skeleton} style={{ height: 260, margin: "var(--sp-4)" }} />
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            {search
              ? "No links match this search."
              : "No links yet. Add an application portal or scholarship page to keep it handy."}
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Title</th>
                <th className={styles.colHide}>Link</th>
                <th className={styles.right}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((link) => (
                <tr key={link.id} className={styles.staticRow}>
                  <td>
                    <div className={styles.name}>{link.title}</div>
                    {link.description && <div className={styles.desc}>{link.description}</div>}
                    <div className={`${styles.sub} ${styles.linkHostSm}`}>{hostOf(link.url)}</div>
                  </td>
                  <td className={styles.colHide}>
                    <a className={styles.linkUrl} href={link.url} target="_blank" rel="noreferrer noopener">
                      {hostOf(link.url)} ↗
                    </a>
                  </td>
                  <td className={styles.right}>
                    <div className={styles.rowActions}>
                      <a
                        className=”btn btn-ghost”
                        href={link.url}
                        target=”_blank”
                        rel=”noreferrer noopener”
                      >
                        Open
                      </a>
                      {canWrite && (
                        <>
                          <button className=”btn btn-ghost” onClick={() => setEditing(link)}>
                            Edit
                          </button>
                          <button
                            className={`btn btn-ghost ${styles.dangerBtn}`}
                            onClick={() => {
                              if (window.confirm(`Delete “${link.title}”?`)) del.mutate(link.id);
                            }}
                            disabled={del.isPending}
                          >
                            Delete
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {!listQ.isLoading && items.length > 0 && (
        <div className={styles.count}>
          {items.length}
          {total > items.length ? ` of ${total}` : ""} link{total === 1 ? "" : "s"}
        </div>
      )}

      {(adding || editing) && (
        <LinkDrawer link={editing} onClose={() => { setAdding(false); setEditing(null); }} />
      )}
    </>
  );
}

function LinkDrawer({ link, onClose }: { link: LinkOut | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: link?.title ?? "",
    url: link?.url ?? "",
    description: link?.description ?? "",
    category: link?.category ?? "general",
  });
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const invalidate = () => qc.invalidateQueries({ queryKey: ["materials-links"] });

  const create = useMutation({
    mutationFn: (body: LinkCreate) => api.post<LinkOut>("/materials/links", body),
    onSuccess: () => { invalidate(); onClose(); },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save the link."),
  });

  const update = useMutation({
    mutationFn: (body: LinkUpdate) => api.patch<LinkOut>(`/materials/links/${link!.id}`, body),
    onSuccess: () => { invalidate(); onClose(); },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save the link."),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const title = form.title.trim();
    const url = form.url.trim();
    if (!title || !url) {
      setError("A title and URL are both required.");
      return;
    }
    const description = form.description.trim() || null;
    const category = form.category.trim() || "general";
    if (link) {
      update.mutate({ title, url, description, category });
    } else {
      create.mutate({ title, url, description, category, is_active: true, sort_order: 0 });
    }
  }

  const pending = create.isPending || update.isPending;

  return (
    <div className={styles.scrim} onClick={onClose}>
      <form className={styles.drawer} onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}>
        <div className={styles.drawerHead}>
          <h2 className={styles.drawerTitle}>{link ? "Edit link" : "Add link"}</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <div className={styles.field}>
          <label className="field-label" htmlFor="link_title">Title</label>
          <input id="link_title" className="input" value={form.title} onChange={set("title")} required autoFocus />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="link_url">URL</label>
          <input
            id="link_url"
            className="input"
            type="url"
            value={form.url}
            onChange={set("url")}
            placeholder="https://…"
            required
          />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="link_category">Category</label>
          <input id="link_category" className="input" value={form.category} onChange={set("category")} />
        </div>

        <div className={styles.field}>
          <label className="field-label" htmlFor="link_desc">Description</label>
          <textarea
            id="link_desc"
            className={styles.noteInput}
            value={form.description}
            onChange={set("description")}
            placeholder="What will a recruit find here? (optional)"
          />
        </div>

        <div className={styles.drawerActions}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={pending}>
            {pending ? "Saving…" : link ? "Save changes" : "Add link"}
          </button>
        </div>
      </form>
    </div>
  );
}
