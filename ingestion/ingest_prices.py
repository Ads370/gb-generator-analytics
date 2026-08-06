"""
Gets MID Market Index Data wholesale prices and writes to bronze layer.
MID is national, returned for a date range in a single call. It is partitioned by
settlement date, like the facts.
"""

import argparse
import logging
from pathlib import Path
from datetime import date, timedelta
import pandas as pd
from ingestion.client import ElexonClient

logger = logging.getLogger(__name__)
BRONZE_DIR = Path("data/bronze/mid")

def daterange(start:date, end:date):
    days = (end - start).days
    for offset in range(days + 1):
        yield start + timedelta(days = offset)

def fetch_date(client:ElexonClient, settlement_date:str) -> pd.DataFrame:
    records = client.get("/datasets/MID", 
                         params={
                             "from": f"{settlement_date}T00:00Z",
                             "to": f"{settlement_date}T23:59Z",
                         },
    )
    if not records:
        logger.warning("No MID data for %s", settlement_date)
        return pd.DataFrame()

    df = pd.json_normalize(records)
    df = df[df["settlementDate"] == settlement_date]
    df["ingested_at"] = pd.Timestamp.now("UTC")
    return df

def write_partition(df: pd.DataFrame, settlement_date:str) -> None:
    if df.empty:
        return
    partition = BRONZE_DIR / f"settlement_date={settlement_date}"
    partition.mkdir(parents=True, exist_ok=True)
    out = partition / "data.parquet"
    df.to_parquet(out, index=False)
    logger.info("Wrote %d rows to %s", len(df), out)

def main() -> None:
    parser = argparse.ArgumentParser(description = "Ingest MID price data")
    parser.add_argument("--from", dest="from_date", help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="End date YYYY-MM-DD")
    parser.add_argument("--lookback_days", type=int, help="Re-pull the last N days")
    args=parser.parse_args()

    if args.lookback_days is not None:
        end = date.today()
        start = end-timedelta(days=args.lookback_days - 1)
    elif args.from_date and args.to_date:
        start = date.fromisoformat(args.from_date)
        end = date.fromisoformat(args.to_date)
    else:
        parser.error("Provide either --loockback-days or both --from and --to")

    client = ElexonClient()
    for day in daterange(start, end):
        settlement_date = day.isoformat()
        logger.info("Fetching MID for %s", settlement_date)
        df = fetch_date(client, settlement_date)
        write_partition(df, settlement_date)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
    