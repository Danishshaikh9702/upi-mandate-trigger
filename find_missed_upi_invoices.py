from env_loader import load_env
from pipeline import find_missed_invoices

load_env()

if __name__ == "__main__":
    result = find_missed_invoices()
    print(result["message"])
    print(f"Successfully generated Excel and {result['batchCount']} JSON files in '{result['outputDir']}'.")
