from env_loader import load_env
from pipeline import convert_excel

load_env()

if __name__ == "__main__":
    result = convert_excel()
    print(result["message"])
    print(f"Successfully generated Excel and {result['batchCount']} JSON files in '{result['outputDir']}'.")
