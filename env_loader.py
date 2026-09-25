import os

EXCEL_DIR = "excel_file"


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


def excel_file_from_env():
    excel_file = os.environ.get("UPI_EXCEL_FILE", "").strip()
    if not excel_file:
        raise SystemExit("UPI_EXCEL_FILE is not set in .env")
    excel_file = excel_file.removesuffix(".xlsx")
    path = os.path.join(EXCEL_DIR, f"{excel_file}.xlsx")
    if not os.path.exists(path):
        raise SystemExit(f"Excel file not found: {path}")
    return path


def db_config_from_env():
    return {
        "host": os.environ["DB_HOST"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "port": int(os.environ.get("DB_PORT", "3306")),
        "database": os.environ.get("DB_NAME", "payment_service"),
    }
