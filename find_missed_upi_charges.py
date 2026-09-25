import json
import math
import os
import shutil

import pandas as pd
import pymysql

from env_loader import db_config_from_env, excel_file_from_env, load_env

load_env()

db = db_config_from_env()
CHARGE_SCHEDULED_ON = os.environ["CHARGE_SCHEDULED_ON"].strip()[:10]
excel_file = excel_file_from_env()


def find_missed_upi_charges():
    print("Connecting to DB...")
    connection = pymysql.connect(
        host=db["host"],
        user=db["user"],
        password=db["password"],
        port=db["port"],
        database=db["database"],
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with connection.cursor() as cursor:
            query = """
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
            """
            cursor.execute(query, (CHARGE_SCHEDULED_ON,))
            results = cursor.fetchall()
            done_customers = set(str(row["customer_id"]) for row in results)
            print(
                f"Found {len(done_customers)} customers to skip "
                "(charged/scheduled or invoice_status REJECT/REJECTED)."
            )
    finally:
        connection.close()

    print("Reading Excel file...")
    df = pd.read_excel(excel_file)
    df["customer_id_str"] = df["customer_id"].astype(str)

    missed_df = df[~df["customer_id_str"].isin(done_customers)].copy()
    print(f"Filtered missed UPI Charge customers: {len(missed_df)} out of {len(df)}")

    output_dir = "missed_upi_charges"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    missed_df.drop(columns=["customer_id_str"], inplace=True)
    missed_df.to_excel(os.path.join(output_dir, "missed_upi_charges.xlsx"), index=False)

    missed_df["customerId"] = missed_df["customer_id"].astype(str)
    missed_df["amount"] = missed_df["Final_nach_amount"].astype(int)
    missed_df.loc[missed_df["amount"] > 14999, "amount"] = 14999

    records = missed_df[["customerId", "amount"]].to_dict(orient="records")

    chunk_size = 2500
    total_chunks = math.ceil(len(records) / chunk_size) if records else 0

    for i in range(total_chunks):
        chunk = records[i * chunk_size : (i + 1) * chunk_size]
        file_name = os.path.join(output_dir, f"batch_{i + 1}.json")
        with open(file_name, "w") as f:
            json.dump(chunk, f, indent=4)

    print(f"Successfully generated Excel and {total_chunks} JSON files in '{output_dir}'.")


if __name__ == "__main__":
    find_missed_upi_charges()
