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
import pandas as pd
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "warehouse.duckdb"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TARGETS = {
    "mart_operator_daily": (
        "operator_daily",
        ["settlement_date", "lead_party_name"],
    ),
    "mart_fuel_mix": (
        "fuel_mix",
        ["settlement_date", "settlement_period", "lead_party_name", "fuel_type"],
    ),
}

TEXT_COLUMNS = {"settlement_date", "lead_party_name", "lead_party_id", "fuel_type"}

def read_existing(spreadsheet, tab_name: str) -> pd.DataFrame:
    try:
        worksheet = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
 
    values = worksheet.get_all_values()
    if len(values) < 2:
        return pd.DataFrame()
 
    header, rows = values[0], values[1:]
    return pd.DataFrame(rows, columns=header)

def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        if column in TEXT_COLUMNS:
            df[column] = df[column].astype(str)
        else:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df
def merge(existing: pd.DataFrame, fresh: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if existing.empty:
        combined = fresh
    else:
        existing = existing.reindex(columns=fresh.columns)
        combined = pd.concat([existing, fresh], ignore_index=True)
 
    combined = combined.drop_duplicates(subset=keys, keep="last")
    return combined.sort_values(keys).reset_index(drop=True)
 
def write(spreadsheet, tab_name: str, df: pd.DataFrame) -> None:
    try:
        worksheet = spreadsheet.worksheet(tab_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=tab_name, rows=len(df) + 100, cols=len(df.columns) + 2
        )
    payload = df.astype(object).where(pd.notna(df), "")
    worksheet.update(
        [df.columns.tolist()] + payload.values.tolist(),
        value_input_option="RAW",
    )

def get_client() -> gspread.Client:
    raw = os.environ["GCP_SA_KEY"]
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes = SCOPES)
    return gspread.authorize(creds)

def main() -> None:
    spreadsheet = get_client().open_by_key(os.environ["SHEET_ID"])
    con = duckdb.connect(str(DB_PATH), read_only=True)
 
    try:
        for mart, (tab_name, keys) in TARGETS.items():
            fresh = con.execute(f"select * from {mart}").fetchdf()
            fresh["settlement_date"] = fresh["settlement_date"].astype(str)
            fresh = coerce_types(fresh)
            existing = read_existing(spreadsheet, tab_name)
            if not existing.empty:
                existing = coerce_types(existing)
 
            combined = merge(existing, fresh, keys)
            write(spreadsheet, tab_name, combined)
            logger.info(
                "Tab '%s': %d existing + %d fresh -> %d rows, %s to %s",
                tab_name,
                len(existing),
                len(fresh),
                len(combined),
                combined["settlement_date"].min(),
                combined["settlement_date"].max(),
            )
    finally:
        con.close()
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
