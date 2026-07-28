"""
Fetch B1610 actual generation per unit and write to bronze, partitioned by date.
One call per settlement period (the endpoint requires it), concatenated into
one file per settlement date. Partitioning by date keeps incremental loads
cheap and lets DuckDB prune by date later.
"""

import logging
import argparse
from pathlib import Path
from datetime import date, timedelta
import pandas as pd # type: ignore
from ingestion.client import ElexonClient

logger = logging.getLogger(__name__)
BRONZE_DIR = Path("data/bronze/b1610")
PERIODS = range(1, 49)  # 48 settlement periods in a day

def fetch_date(client: ElexonClient, settlement_date: str) -> pd.DataFrame:
    """Fetch all settlement periods for a given date, return one DataFrame."""
    frames = []
    for period in PERIODS:
        records = client.get(
            "/datasets/B1610",
            params={"settlementDate": settlement_date, "settlementPeriod": period},
        )
        if records: 
            frames.append(pd.json_normalize(records))

    if not frames:
        logger.warning("No data found for %s", settlement_date)
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["ingested_at"] = pd.Timestamp.now("UTC")
    return df

def write_partition(df: pd.DataFrame, settlement_date: str) -> None:
    """Writes a DataFrame to a parquet file partitioned by settlement date."""
    if df.empty:
        return
    partition = BRONZE_DIR / f"settlement_date={settlement_date}"
    partition.mkdir(parents=True, exist_ok=True)
    out = partition / "data.parquet"
    df.to_parquet(out, index=False)
    logger.info("Wrote %d records to %s", len(df), out)

def daterange(start: date, end: date):
    """Yield each date from start to end, inclusive."""
    days = (end - start).days
    for offset in range(days + 1):
        yield start + timedelta(days=offset)

def main() -> None:
    parser = argparse.ArgumentParser(description = "Ingest B1610 generation data")
    parser.add_argument("--from", dest="from_date", help="Start date YYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="End date YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, help="Re-pull the last N days ending today")
    args = parser.parse_args()

    if args.lookback_days is not None:
        end = date.today()
        start = end - timedelta(days=args.lookback_days - 1)
    elif args.from_date and args.to_date:
        start = date.fromisoformat(args.from_date)
        end = date.fromisoformat(args.to_date)
    else:
        parser.error("Must specify either --lookback-days or both --from and --to")

    client = ElexonClient()
    for day in daterange(start, end):
        settlement_date = day.isoformat()
        logger.info("Fetching data for %s", settlement_date)
        df = fetch_date(client, settlement_date)
        write_partition(df, settlement_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()