"""
Exports dbt marts from DuckDB to CSV for Tableau Public Desktop
Reads each mart from warehouse.duckdb and wirtes a CSV into data/exports/, which tableau opens directly.

"""

import logging
from pathlib import Path
import duckdb

logger = logging.getLogger(__name__)
DB_PATH = "warehouse.duckdb"
EXPORT_DIR = Path("data/exports")

MARTS = [
    "mart_operator_period",
    "mart_fuel_mix",
    "mart_national_period",
    "mart_operator_revenue",
]

def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        for mart in MARTS:
            out = EXPORT_DIR / f"{mart}.csv"
            con.execute(f"copy {mart} to '{out}' (header, delimiter ',')")
            rows = con.execute(f"select count(*) from {mart}").fetchone()[0]
            logger.info("Exported %d rows to %s", rows, out)
    finally:
        con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()