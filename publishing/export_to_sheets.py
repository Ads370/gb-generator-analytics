"""
Push daily operator mart to a Google Sheet for Tableau Public.
Tableau public can only auto-refresh from Google Sheets, so this is the
publish target. Credentials come from the GCP_SA_KEY env var (a GitHub secret in CI), not
a file from the repo.
"""

import json
import logging
import os
from pathlib import Path
import duckdb
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "warehouse.duckdb"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TARGETS = {
    "mart_operator_daily": "operator_daily",
}

def get_client() -> gspread.Client:
    raw = os.environ["GCP_SA_KEY"]
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes = SCOPES)
    return gspread.authorize(creds)

def main() -> None:
    sheet_id = os.environ["SHEET_ID"]
    client = get_client()
    spreadsheet = client.open_by_key(sheet_id)

    con = duckdb.connect(str(DB_PATH), read_only = True)
    try:
        for mart, tab_name in TARGETS.items():
            df = con.execute(f"select * from {mart}").fetchdf()
            df = df.fillna("").astype(str)
            try:
                worksheet = spreadsheet.worksheet(tab_name)
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=tab_name, rows = len(df) + 10, cols=len(df.columns) + 2
                )

            worksheet.update(
                [df.columns.tolist()] + df.values.tolist(),
                value_input_option="RAW",
            )
            logger.info("Pushed %d rows to tab '%s'", len(df), tab_name)
    finally:
        con.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
