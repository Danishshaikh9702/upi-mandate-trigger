import json
import math
import os
import shutil

import pandas as pd

from env_loader import excel_file_from_env, load_env

load_env()

excel_file = excel_file_from_env()
output_dir = "upi_charge_payloads"

print("Reading Excel file...")
df = pd.read_excel(excel_file)

if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)

df.to_excel(os.path.join(output_dir, "upi_charge_payload.xlsx"), index=False)

df["customerId"] = df["customer_id"].astype(str)
df["amount"] = df["Final_nach_amount"].astype(int)
df.loc[df["amount"] > 14999, "amount"] = 14999

records = df[["customerId", "amount"]].to_dict(orient="records")

chunk_size = 2500
total_chunks = math.ceil(len(records) / chunk_size) if records else 0

for i in range(total_chunks):
    chunk = records[i * chunk_size : (i + 1) * chunk_size]
    file_name = os.path.join(output_dir, f"batch_{i + 1}.json")
    with open(file_name, "w") as f:
        json.dump(chunk, f, indent=4)

print(f"Successfully generated Excel and {total_chunks} JSON files in '{output_dir}'.")
