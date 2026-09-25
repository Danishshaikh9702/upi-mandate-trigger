import json
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from env_loader import EXCEL_DIR, archive_excel, keep_single_excel, list_excel_files, load_env
from pipeline import OUTPUTS, convert_excel, find_missed_charges, find_missed_invoices

load_env()

DASHBOARD_URL = "https://prod.zype.co.in/api/v1/dashboard/"

app = FastAPI(title="upi-mandate-trigger")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    excelName: str | None = None
    scheduledOn: str | None = None


@app.get("/api/status")
def status():
    current, _ = keep_single_excel()
    return {
        "excelFile": current.replace(".xlsx", "") if current else "",
        "excelFiles": [current] if current else [],
        "chargeDate": os.environ.get("CHARGE_SCHEDULED_ON", "")[:10],
        "invoiceDate": os.environ.get("INVOICE_SCHEDULED_ON", "")[:10],
        "dashboardUrl": DASHBOARD_URL,
    }


@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Upload an .xlsx file")
    os.makedirs(EXCEL_DIR, exist_ok=True)
    new_name = os.path.basename(file.filename)
    archived = []
    for old_name in list_excel_files():
        dest = archive_excel(old_name)
        if dest:
            archived.append(os.path.basename(dest))
    dest = os.path.join(EXCEL_DIR, new_name)
    with open(dest, "wb") as out:
        out.write(await file.read())
    return {
        "file": new_name,
        "excelFiles": [new_name],
        "archived": archived,
        "message": (
            f"Saved {new_name}. Moved {', '.join(archived)} to delete_excel_file/."
            if archived
            else f"Saved {new_name} in excel_file/."
        ),
    }


@app.post("/api/convert")
def convert(body: RunRequest):
    try:
        return convert_excel(body.excelName)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/missed-charges")
def missed_charges(body: RunRequest):
    try:
        return find_missed_charges(body.scheduledOn, body.excelName)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/missed-invoices")
def missed_invoices(body: RunRequest):
    try:
        return find_missed_invoices(body.scheduledOn, body.excelName)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/batches/{kind}")
def list_batches(kind: str):
    if kind not in OUTPUTS:
        raise HTTPException(404, "Unknown output")
    folder = OUTPUTS[kind]["dir"]
    if not os.path.isdir(folder):
        return {"kind": kind, "dir": folder, "files": []}
    files = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        files.append({"file": name, "bytes": os.path.getsize(path)})
    return {"kind": kind, "dir": folder, "files": files}


@app.get("/api/batches/{kind}/{file_name}")
def read_batch(kind: str, file_name: str):
    if kind not in OUTPUTS or "/" in file_name or "\\" in file_name:
        raise HTTPException(404, "Unknown file")
    path = os.path.join(OUTPUTS[kind]["dir"], file_name)
    if not os.path.isfile(path):
        raise HTTPException(404, "File not found")
    if file_name.endswith(".json"):
        with open(path) as f:
            data = json.load(f)
        return {"file": file_name, "records": len(data), "preview": data[:20], "payload": data}
    raise HTTPException(400, "Only JSON batches can be previewed")


if os.path.isdir("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="ui")
