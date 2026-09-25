import os
import shutil
from datetime import datetime

EXCEL_DIR = "excel_file"
DELETED_EXCEL_DIR = "delete_excel_file"


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def list_excel_files():
    if not os.path.isdir(EXCEL_DIR):
        return []
    return sorted(name for name in os.listdir(EXCEL_DIR) if name.endswith(".xlsx"))


def archive_excel(file_name):
    source = os.path.join(EXCEL_DIR, file_name)
    if not os.path.isfile(source):
        return None
    os.makedirs(DELETED_EXCEL_DIR, exist_ok=True)
    dest = os.path.join(DELETED_EXCEL_DIR, file_name)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(file_name)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(DELETED_EXCEL_DIR, f"{stem}_{stamp}{ext}")
    shutil.move(source, dest)
    return dest


def keep_single_excel(keep_name=None):
    files = list_excel_files()
    if keep_name:
        archived = []
        for name in files:
            if name != keep_name:
                archived.append(archive_excel(name))
        return keep_name if os.path.isfile(os.path.join(EXCEL_DIR, keep_name)) else None, archived

    if not files:
        return None, []
    if len(files) == 1:
        return files[0], []

    newest = max(files, key=lambda name: os.path.getmtime(os.path.join(EXCEL_DIR, name)))
    archived = [archive_excel(name) for name in files if name != newest]
    return newest, archived


def excel_file_from_env(name=None):
    if name:
        excel_file = name.strip().removesuffix(".xlsx")
        path = os.path.join(EXCEL_DIR, f"{excel_file}.xlsx")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Excel file not found: {path}")
        return path

    current, _ = keep_single_excel()
    if current:
        return os.path.join(EXCEL_DIR, current)

    excel_file = os.environ.get("UPI_EXCEL_FILE", "").strip()
    if not excel_file:
        raise ValueError("No Excel file in excel_file/. Upload one or set UPI_EXCEL_FILE in .env")
    excel_file = excel_file.removesuffix(".xlsx")
    path = os.path.join(EXCEL_DIR, f"{excel_file}.xlsx")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Excel file not found: {path}")
    return path


def db_config_from_env():
    return {
        "host": os.environ["DB_HOST"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "port": int(os.environ.get("DB_PORT", "3306")),
        "database": os.environ.get("DB_NAME", "payment_service"),
    }
