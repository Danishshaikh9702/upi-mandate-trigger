import json
import math
import os
import shutil

import pandas as pd
import pymysql

from env_loader import db_config_from_env, excel_file_from_env

CHUNK_SIZE = 2500
AMOUNT_CAP = 14999

OUTPUTS = {
    "convert": {
        "dir": "upi_charge_payloads",
        "excel": "upi_charge_payload.xlsx",
    },
    "charges": {
        "dir": "missed_upi_charges",
        "excel": "missed_upi_charges.xlsx",
    },
    "invoices": {
        "dir": "missed_upi_invoices",
        "excel": "missed_upi_invoices.xlsx",
    },
}


def _reset_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def _write_batches(df, output_dir, excel_name):
    _reset_dir(output_dir)
    df.to_excel(os.path.join(output_dir, excel_name), index=False)

    payload = df.copy()
    payload["customerId"] = payload["customer_id"].astype(str)
    payload["amount"] = payload["Final_nach_amount"].astype(int)
    payload.loc[payload["amount"] > AMOUNT_CAP, "amount"] = AMOUNT_CAP
    records = payload[["customerId", "amount"]].to_dict(orient="records")

    total_chunks = math.ceil(len(records) / CHUNK_SIZE) if records else 0
    batches = []
    for i in range(total_chunks):
        chunk = records[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
        file_name = f"batch_{i + 1}.json"
        with open(os.path.join(output_dir, file_name), "w") as f:
            json.dump(chunk, f, indent=4)
        batches.append({"file": file_name, "records": len(chunk)})

    return {
        "outputDir": output_dir,
        "excelFile": excel_name,
        "totalRecords": len(records),
        "batchCount": total_chunks,
        "batches": batches,
    }


def convert_excel(excel_name=None):
    excel_path = excel_file_from_env(excel_name)
    df = pd.read_excel(excel_path)
    result = _write_batches(df, OUTPUTS["convert"]["dir"], OUTPUTS["convert"]["excel"])
    result["sourceExcel"] = os.path.basename(excel_path)
    result["skipped"] = 0
    result["message"] = f"Generated {result['batchCount']} JSON file(s) from {result['sourceExcel']}."
    return result


def _connect():
    db = db_config_from_env()
    return pymysql.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        port=db["port"],
        database=db["database"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def find_missed_charges(scheduled_on=None, excel_name=None):
    date = (scheduled_on or os.environ["CHARGE_SCHEDULED_ON"]).strip()[:10]
    excel_path = excel_file_from_env(excel_name)
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT customer_id
                FROM payment_service.enach_orders
                WHERE DATE(scheduled_on) = %s
                  AND (
                    (
                      payment_gateway_provider IN ('BILLDESK', 'PHONEPE')
                      AND remark = 'Charge Subscription'
                    )
                    OR invoice_status IN ('REJECTED')
                  )
                """,
                (date,),
            )
            done_customers = set(str(row["customer_id"]) for row in cursor.fetchall())
    finally:
        connection.close()

    df = pd.read_excel(excel_path)
    df["customer_id_str"] = df["customer_id"].astype(str)
    missed_df = df[~df["customer_id_str"].isin(done_customers)].copy()
    missed_df.drop(columns=["customer_id_str"], inplace=True)

    result = _write_batches(
        missed_df, OUTPUTS["charges"]["dir"], OUTPUTS["charges"]["excel"]
    )
    result["sourceExcel"] = os.path.basename(excel_path)
    result["scheduledOn"] = date
    result["skipped"] = len(done_customers)
    result["message"] = (
        f"Missed {result['totalRecords']} of {len(df)} customers on {date}. "
        f"Skipped {len(done_customers)} charged or REJECTED."
    )
    return result


def find_missed_invoices(scheduled_on=None, excel_name=None):
    date = (scheduled_on or os.environ["INVOICE_SCHEDULED_ON"]).strip()[:10]
    excel_path = excel_file_from_env(excel_name)
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT customer_id
                FROM payment_service.enach_orders
                WHERE DATE(scheduled_on) = %s
                """,
                (date,),
            )
            done_customers = set(str(row["customer_id"]) for row in cursor.fetchall())
    finally:
        connection.close()

    df = pd.read_excel(excel_path)
    df["customer_id_str"] = df["customer_id"].astype(str)
    missed_df = df[~df["customer_id_str"].isin(done_customers)].copy()
    missed_df.drop(columns=["customer_id_str"], inplace=True)

    result = _write_batches(
        missed_df, OUTPUTS["invoices"]["dir"], OUTPUTS["invoices"]["excel"]
    )
    result["sourceExcel"] = os.path.basename(excel_path)
    result["scheduledOn"] = date
    result["skipped"] = len(done_customers)
    result["message"] = (
        f"Missed {result['totalRecords']} of {len(df)} customers on {date}. "
        f"Skipped {len(done_customers)} already invoiced."
    )
    return result
