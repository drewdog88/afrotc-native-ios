/* Bulk import wizard — bring a roster in from a spreadsheet in three steps:
   pick a CSV/Excel file, submit it to /recruits/import, then review the per-row
   result. A successful run writes recruits, so we invalidate the roster + dashboard
   tiles that depend on them. */
import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import type { components } from "../api/schema";
import styles from "./ImportRecruits.module.css";

type ImportResult = components["schemas"]["ImportResult"];

const EXPECTED_COLUMNS = [
  "first_name",
  "last_name",
  "email",
  "phone",
  "current_school",
  "school_type",
  "stage",
];

const STEPS = ["Upload", "Review", "Done"] as const;
type Step = 0 | 1 | 2;

const ACCEPT = ".csv,.xlsx,.xls";

function isAcceptedFile(name: string): boolean {
  const lower = name.toLowerCase();
  return lower.endsWith(".csv") || lower.endsWith(".xlsx") || lower.endsWith(".xls");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ImportRecruits() {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>(0);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const runImport = useMutation({
    mutationFn: (f: File) => {
      const form = new FormData();
      form.append("file", f);
      return api.postForm<ImportResult>("/recruits/import", form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recruits"] });
      qc.invalidateQueries({ queryKey: ["funnel"] });
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Couldn't import that file. Check the format and try again."),
  });

  const result = runImport.data;

  function chooseFile(next: File | null) {
    setPickError(null);
    if (!next) return;
    if (!isAcceptedFile(next.name)) {
      setPickError("Choose a .csv or .xlsx file.");
      return;
    }
    setFile(next);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files?.[0] ?? null;
    chooseFile(dropped);
  }

  function submit() {
    if (!file) return;
    setError(null);
    runImport.mutate(file, {
      onSuccess: () => setStep(2),
    });
    setStep(1);
  }

  function reset() {
    setFile(null);
    setPickError(null);
    setError(null);
    runImport.reset();
    setStep(0);
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Import recruits</h1>
          <p className={styles.subtitle}>
            Bring a whole roster in at once from a spreadsheet — we'll flag any rows that need a fix.
          </p>
        </div>
        <Link to="/recruits" className="btn btn-ghost">Back to recruits</Link>
      </div>

      <ol className={styles.stepper} aria-label="Import progress">
        {STEPS.map((label, i) => {
          const state = i < step ? "done" : i === step ? "active" : "upcoming";
          return (
            <li
              key={label}
              className={`${styles.step} ${styles[state]}`}
              aria-current={i === step ? "step" : undefined}
            >
              <span className={styles.stepDot}>{i < step ? "✓" : i + 1}</span>
              <span className={styles.stepLabel}>{label}</span>
            </li>
          );
        })}
      </ol>

      <section className={`card ${styles.panel}`}>
        {step === 0 && (
          <UploadStep
            file={file}
            dragging={dragging}
            pickError={pickError}
            inputRef={inputRef}
            onOpenPicker={() => inputRef.current?.click()}
            onPick={(e) => chooseFile(e.target.files?.[0] ?? null)}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClear={() => {
              setFile(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            onContinue={submit}
          />
        )}

        {step === 1 && (
          <ReviewStep
            pending={runImport.isPending}
            error={error}
            result={result}
            onRetry={submit}
            onBack={() => {
              setError(null);
              setStep(0);
            }}
            onFinish={() => setStep(2)}
          />
        )}

        {step === 2 && result && <DoneStep result={result} onReset={reset} />}
      </section>
    </div>
  );
}

/* ---- Step 1: choose a file ---- */
function UploadStep(props: {
  file: File | null;
  dragging: boolean;
  pickError: string | null;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onOpenPicker: () => void;
  onPick: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDragOver: (e: DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: DragEvent) => void;
  onClear: () => void;
  onContinue: () => void;
}) {
  const {
    file,
    dragging,
    pickError,
    inputRef,
    onOpenPicker,
    onPick,
    onDragOver,
    onDragLeave,
    onDrop,
    onClear,
    onContinue,
  } = props;

  return (
    <div className={styles.stepBody}>
      <div
        className={`${styles.dropzone} ${dragging ? styles.dropzoneActive : ""}`}
        role="button"
        tabIndex={0}
        aria-label="Choose a CSV or Excel file, or drop one here"
        onClick={onOpenPicker}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onOpenPicker();
          }
        }}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className={styles.hiddenInput}
          onChange={onPick}
        />
        <div className={styles.dropIcon} aria-hidden>⬆</div>
        {file ? (
          <>
            <div className={styles.fileName}>{file.name}</div>
            <div className={styles.fileMeta}>{formatBytes(file.size)}</div>
          </>
        ) : (
          <>
            <div className={styles.dropTitle}>Drop a file here or click to browse</div>
            <div className={styles.dropHint}>CSV or Excel (.csv, .xlsx)</div>
          </>
        )}
      </div>

      {pickError && <div className={styles.formError}>{pickError}</div>}

      <div className={styles.columnsHint}>
        <div className="eyebrow">Expected columns</div>
        <div className={styles.chips}>
          {EXPECTED_COLUMNS.map((c) => (
            <code key={c} className={styles.colChip}>{c}</code>
          ))}
        </div>
        <p className={styles.hintNote}>
          The first row should be a header. Extra columns are ignored; email and phone can be blank.
        </p>
      </div>

      <div className={styles.actions}>
        {file && (
          <button type="button" className="btn btn-ghost" onClick={onClear}>
            Choose a different file
          </button>
        )}
        <button
          type="button"
          className="btn btn-primary"
          disabled={!file}
          onClick={onContinue}
        >
          Import file
        </button>
      </div>
    </div>
  );
}

/* ---- Step 2: submitting + per-row result ---- */
function ReviewStep(props: {
  pending: boolean;
  error: string | null;
  result: ImportResult | undefined;
  onRetry: () => void;
  onBack: () => void;
  onFinish: () => void;
}) {
  const { pending, error, result, onRetry, onBack, onFinish } = props;

  if (pending) {
    return (
      <div className={styles.stepBody}>
        <div className={styles.skeleton} style={{ height: 96 }} />
        <div className={styles.skeleton} style={{ height: 220 }} />
        <p className={styles.centerMuted}>Reading your file and creating recruits…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.stepBody}>
        <div className={styles.formError}>{error}</div>
        <div className={styles.actions}>
          <button type="button" className="btn btn-ghost" onClick={onBack}>Back</button>
          <button type="button" className="btn btn-primary" onClick={onRetry}>Try again</button>
        </div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className={styles.stepBody}>
      <ResultSummary result={result} />
      {result.errors.length > 0 ? (
        <div className={styles.errorsBlock}>
          <div className="eyebrow">Rows that need a fix</div>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.rowCol}>Row</th>
                  <th>What went wrong</th>
                </tr>
              </thead>
              <tbody>
                {result.errors.map((rowErr) => (
                  <tr key={rowErr.row}>
                    <td className={`${styles.rowCol} mono`}>{rowErr.row}</td>
                    <td>
                      <ul className={styles.msgList}>
                        {rowErr.errors.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.hintNote}>
            Fix these rows in your spreadsheet and import again — imported rows won't be duplicated if they
            already exist.
          </p>
        </div>
      ) : (
        <div className={styles.empty}>Every row imported cleanly. Nice work.</div>
      )}

      <div className={styles.actions}>
        <button type="button" className="btn btn-ghost" onClick={onBack}>Import another file</button>
        <button type="button" className="btn btn-primary" onClick={onFinish}>Continue</button>
      </div>
    </div>
  );
}

/* ---- Step 3: summary ---- */
function DoneStep({ result, onReset }: { result: ImportResult; onReset: () => void }) {
  const clean = result.failed === 0;
  return (
    <div className={styles.stepBody}>
      <div className={styles.doneWrap}>
        <div className={`${styles.doneBadge} ${clean ? styles.badgeOk : styles.badgeWarn}`} aria-hidden>
          {clean ? "✓" : "!"}
        </div>
        <h2 className={styles.doneTitle}>
          {clean ? "Import complete" : "Import finished with some skipped rows"}
        </h2>
        <p className={styles.doneCopy}>
          {result.imported === 0
            ? "No new recruits were added."
            : `Added ${result.imported} recruit${result.imported === 1 ? "" : "s"} to your pipeline.`}
          {result.failed > 0 && ` ${result.failed} row${result.failed === 1 ? "" : "s"} were skipped.`}
        </p>
      </div>

      <ResultSummary result={result} />

      <div className={styles.actions}>
        <button type="button" className="btn btn-ghost" onClick={onReset}>Import another file</button>
        <Link to="/recruits" className="btn btn-primary">View recruits</Link>
      </div>
    </div>
  );
}

/* ---- Shared: the three-count readout ---- */
function ResultSummary({ result }: { result: ImportResult }) {
  const stats: { label: string; value: number; tone?: "ok" | "warn" }[] = [
    { label: "Imported", value: result.imported, tone: "ok" },
    { label: "Skipped", value: result.failed, tone: result.failed > 0 ? "warn" : undefined },
    { label: "Total rows", value: result.total_rows },
  ];
  return (
    <div className={styles.summary}>
      {stats.map((s) => (
        <div key={s.label} className={styles.stat}>
          <div
            className={`mono ${styles.statValue} ${
              s.tone === "ok" ? styles.valueOk : s.tone === "warn" ? styles.valueWarn : ""
            }`}
          >
            {s.value}
          </div>
          <div className={styles.statLabel}>{s.label}</div>
        </div>
      ))}
    </div>
  );
}
