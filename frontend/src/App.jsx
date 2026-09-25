import { useEffect, useState } from "react";
import { api } from "./api";

const PAGES = [
  ["overview", "01", "Process"],
  ["convert", "02", "Convert Excel"],
  ["charges", "03", "Missed charges"],
  ["invoices", "04", "Missed invoices"],
  ["batches", "05", "Batches"],
];

const DASHBOARD = "https://prod.zype.co.in/api/v1/dashboard/";

export default function App() {
  const [page, setPage] = useState("overview");
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  async function refreshStatus() {
    try {
      setStatus(await api.status());
    } catch (exc) {
      setError(exc.message);
    }
  }

  useEffect(() => {
    refreshStatus();
  }, []);

  const current = PAGES.find(([id]) => id === page);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">UPI</span>
          <div>
            <p className="eyebrow">Respo payments</p>
            <h1>eNACH desk</h1>
          </div>
        </div>
        <p className="lede">Invoice on T-2. Charge on T. Reconcile on T+1. One Excel. 2500 IDs per trigger.</p>
        <nav>
          {PAGES.map(([id, num, label]) => (
            <button key={id} className={page === id ? "active" : ""} onClick={() => setPage(id)}>
              <span>{num}</span>
              {label}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <p>Live file</p>
          <strong>{status?.excelFiles?.[0] || "No Excel yet"}</strong>
          <a className="dash-link" href={status?.dashboardUrl || DASHBOARD} target="_blank" rel="noreferrer">
            Open job dashboard →
          </a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="crumb">Operations / {current?.[2]}</p>
            <h2>{current?.[2]}</h2>
          </div>
          <div className="top-pills">
            <span>Charge {status?.chargeDate || "—"}</span>
            <span>Invoice {status?.invoiceDate || "—"}</span>
            <span>Max 2500 / batch</span>
          </div>
        </header>
        <main>
          {error && <p className="banner error">{error}</p>}
          {page === "overview" && <Overview status={status} />}
          {page === "convert" && <RunPanel kind="convert" status={status} onDone={refreshStatus} />}
          {page === "charges" && <RunPanel kind="charges" status={status} onDone={refreshStatus} />}
          {page === "invoices" && <RunPanel kind="invoices" status={status} onDone={refreshStatus} />}
          {page === "batches" && <Batches status={status} />}
        </main>
      </div>
    </div>
  );
}

function Overview({ status }) {
  return (
    <section>
      <p className="intro">
        Due dates are the 2nd, 5th, 8th, 11th, and last day of the month. Run from this UI or the same Python commands.
      </p>
      <div className="timeline">
        <article>
          <span className="step">T-2</span>
          <h3>Create invoice</h3>
          <code>generation-billdesk-bulk-invoices-for-customer-list-job</code>
          <p>Do not run this job on T-1. That cancels invoices already created.</p>
        </article>
        <article className="featured">
          <span className="step">T</span>
          <h3>UPI charge</h3>
          <code>generation-billdesk-bulk-enach-order-for-customer-list-job</code>
          <p>Trigger once per due date. Skip REJECTED invoices.</p>
        </article>
        <article>
          <span className="step">T+1</span>
          <h3>Reconcile</h3>
          <code>reconcile-pending-enach-order-payment-statuses</code>
          <p>Use customerId + orderId for pending rows.</p>
        </article>
      </div>
      <div className="meta-grid">
        <div>
          <h4>Current Excel</h4>
          <p>{status?.excelFiles?.[0] || "None in excel_file/"}</p>
        </div>
        <div>
          <h4>Charge date</h4>
          <p>{status?.chargeDate || "—"}</p>
        </div>
        <div>
          <h4>Invoice date</h4>
          <p>{status?.invoiceDate || "—"}</p>
        </div>
        <div>
          <h4>Replaced files</h4>
          <p>delete_excel_file/</p>
        </div>
      </div>
    </section>
  );
}

function RunPanel({ kind, status, onDone }) {
  const isConvert = kind === "convert";
  const isCharges = kind === "charges";
  const [excelName, setExcelName] = useState("");
  const [scheduledOn, setScheduledOn] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [openBatch, setOpenBatch] = useState(null);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    setExcelName(status?.excelFile || "");
    setScheduledOn(isCharges ? status?.chargeDate || "" : status?.invoiceDate || "");
  }, [status, isCharges]);

  const blurb = {
    convert: "Reads the one file in excel_file/ and writes batches of 2500 to upi_charge_payloads/.",
    charges: "Compares the Excel with Charge Subscription / REJECTED rows on the charge date.",
    invoices: "Compares the Excel with enach_orders on the invoice date.",
  }[kind];

  async function run() {
    setBusy(true);
    setError("");
    setResult(null);
    setOpenBatch(null);
    setCopied("");
    try {
      const data = isConvert
        ? await api.convert({ scheduledOn })
        : isCharges
          ? await api.missedCharges({ scheduledOn })
          : await api.missedInvoices({ scheduledOn });
      setResult(data);
      onDone?.();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  async function openJson(batchKind, file) {
    setError("");
    setCopied("");
    try {
      setOpenBatch(await api.batch(batchKind, file));
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function copyJson(batchKind, file) {
    setError("");
    try {
      const data = await api.batch(batchKind, file);
      setOpenBatch(data);
      await navigator.clipboard.writeText(JSON.stringify(data.payload, null, 4));
      setCopied(`Copied ${file}. Paste it into the dashboard.`);
    } catch (exc) {
      setError(exc.message);
    }
  }

  async function onUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const data = await api.uploadExcel(file);
      setExcelName(data.file.replace(/\.xlsx$/, ""));
      setNotice(data.message || `Saved ${data.file}. Old file moved to delete_excel_file/.`);
      onDone?.();
    } catch (exc) {
      setError(exc.message);
    }
  }

  return (
    <section>
      <p className="intro">{blurb}</p>
      <div className="card form-card">
        <label>
          Current Excel
          <input value={status?.excelFiles?.[0] || excelName || "No file yet"} readOnly />
        </label>
        <label className="upload">
          Replace Excel
          <input type="file" accept=".xlsx" onChange={onUpload} />
        </label>
        {!isConvert && (
          <label>
            Scheduled on
            <input type="date" value={scheduledOn} onChange={(e) => setScheduledOn(e.target.value)} />
          </label>
        )}
        <button className="primary" disabled={busy} onClick={run}>
          {busy ? "Running…" : "Run job"}
        </button>
      </div>
      {notice && <p className="banner ok">{notice}</p>}
      {error && <p className="banner error">{error}</p>}
      {result && (
        <div className="card result">
          <p className="result-msg">{result.message}</p>
          <div className="stat-row">
            <div>
              <h4>Records</h4>
              <p>{result.totalRecords}</p>
            </div>
            <div>
              <h4>Batches</h4>
              <p>{result.batchCount}</p>
            </div>
            <div>
              <h4>Folder</h4>
              <p>{result.outputDir}</p>
            </div>
            {result.skipped != null && (
              <div>
                <h4>Skipped</h4>
                <p>{result.skipped}</p>
              </div>
            )}
          </div>
          <h3>JSON files</h3>
          <p className="hint">Open a file here, then Copy it for the dashboard. Max 2500 IDs per file.</p>
          <ul className="batch-list">
            {(result.batches || []).map((batch) => (
              <li key={batch.file}>
                <span>
                  {batch.file}
                  <em>{batch.records} customers</em>
                </span>
                <button type="button" onClick={() => openJson(kind, batch.file)}>
                  Open
                </button>
                <button type="button" className="primary" onClick={() => copyJson(kind, batch.file)}>
                  Copy
                </button>
              </li>
            ))}
          </ul>
          {copied && <p className="banner ok">{copied}</p>}
          {openBatch && (
            <div className="json-view">
              <div className="json-head">
                <p>
                  {openBatch.file} — {openBatch.records} records
                </p>
                <button type="button" className="primary" onClick={() => copyJson(kind, openBatch.file)}>
                  Copy
                </button>
              </div>
              <pre>{JSON.stringify(openBatch.payload, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Batches({ status }) {
  const [kind, setKind] = useState("convert");
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState(null);
  const [copied, setCopied] = useState("");

  async function load(nextKind = kind) {
    const data = await api.batches(nextKind);
    setFiles(data.files || []);
    setSelected(null);
  }

  useEffect(() => {
    load(kind).catch(() => setFiles([]));
  }, [kind]);

  async function openFile(file) {
    if (!file.endsWith(".json")) return;
    setSelected(await api.batch(kind, file));
    setCopied("");
  }

  async function copyFile(file) {
    if (!file.endsWith(".json")) return;
    const data = await api.batch(kind, file);
    setSelected(data);
    await navigator.clipboard.writeText(JSON.stringify(data.payload, null, 4));
    setCopied(`Copied ${file}`);
  }

  async function copyPayload() {
    if (!selected?.payload) return;
    await navigator.clipboard.writeText(JSON.stringify(selected.payload, null, 4));
    setCopied(`Copied ${selected.file}`);
  }

  return (
    <section>
      <p className="intro">
        Each JSON file is at most 2500 customers. Trigger jobs at{" "}
        <a href={status?.dashboardUrl || DASHBOARD} target="_blank" rel="noreferrer">
          prod.zype.co.in dashboard
        </a>
        .
      </p>
      <div className="tabs">
        {[
          ["convert", "Charge payloads"],
          ["charges", "Missed charges"],
          ["invoices", "Missed invoices"],
        ].map(([id, label]) => (
          <button key={id} className={kind === id ? "active" : ""} onClick={() => setKind(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="split">
        <div className="card">
          <h3>Files</h3>
          {!files.length && <p className="hint">No output yet. Run a job first.</p>}
          <ul className="batch-list">
            {files.map((item) => (
              <li key={item.file}>
                <span>{item.file}</span>
                {item.file.endsWith(".json") ? (
                  <>
                    <button type="button" onClick={() => openFile(item.file)}>
                      Open
                    </button>
                    <button type="button" className="primary" onClick={() => copyFile(item.file)}>
                      Copy
                    </button>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
        <div className="card preview-card">
          <h3>{selected?.file || "Preview"}</h3>
          {selected ? (
            <>
              <p className="hint">{selected.records} records in this batch.</p>
              <div className="actions">
                <button type="button" className="primary" onClick={copyPayload}>
                  Copy
                </button>
                <a className="secondary" href={status?.dashboardUrl || DASHBOARD} target="_blank" rel="noreferrer">
                  Open dashboard
                </a>
              </div>
              {copied && <p className="banner ok">{copied}</p>}
              <pre>{JSON.stringify(selected.preview, null, 2)}</pre>
            </>
          ) : (
            <p className="hint">Select a batch_*.json file to preview and copy.</p>
          )}
        </div>
      </div>
    </section>
  );
}
