"""Fetch BM Unit reference table and write it to bronze as parquet.
This is the operator lookup. Every generation unit maps. to a lead party (the company).
It is overwritten in full each run, since its current standing data rather than a time series.
"""

import logging
from pathlib import Path
import pandas as pd
from ingestion.client import ElexonClient


logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("data/bronze/bmunits")
OUTPUT_FILE = OUTPUT_DIR / "bmunits.parquet"

def main() -> None:
    client = ElexonClient()
    units = client.get("/reference/bmunits/all")
    df = pd.json_normalize(units)
    df["ingested_at"] = pd.Timestamp.now("UTC")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)
    logger.info("Wrote %d units to %s", len(df), OUTPUT_FILE)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
