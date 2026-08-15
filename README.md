# GB Generator Analytics
 
An end-to-end data pipeline that benchmarks Great Britain's electricity generators against each other on output, asset utilisation, fuel mix, and the market value of what they produce. Data is pulled from Elexon's public settlement feeds every day, transformed and tested with dbt, and published to a live dashboard.
 
**Stack:** Python · DuckDB · dbt · GitHub Actions · Google Sheets · Tableau Public
**Cost to run:** £0
 
---
 
## The problem
 
Britain's electricity market is unusually transparent. Elexon publishes half-hourly generation output for every registered generating unit, along with wholesale prices, and it is all free.
 
The catch is that none of it is analysis-ready.
 
- Output is reported per **generating unit** (`T_TORN-1`), not per company. Answering "how did EDF perform against RWE" means joining against a separate register to find out who owns what.
- The core generation dataset requires one API call per half-hour period, so a single day is 48 requests.
- Values are **restated** as the settlement process runs, so the number you pulled yesterday may not be the number today.
- Data is published with a lag of several days, so "yesterday" is usually empty.
- Roughly a fifth of volume is registered to trading and aggregation companies that have no fuel type at all, because they do not own physical plant.
So the question this project answers is:
 
> How do GB electricity generators compare on volume, asset utilisation, fuel mix, and the market value of their output, and how does that change hour by hour?
 
## The answer
 
The pipeline produces an operator-level view that makes the comparison possible. Three findings fall straight out of it.
 
### Load factor separates three different business models
 
Load factor is how much a company actually generated as a fraction of what its plant could have produced running flat out. A value of 1.0 means every unit ran at full power the whole time. A value of 0.2 means it was mostly idle.
 
Sorting operators by it splits them into groups that map onto genuinely different ways of making money:
 
- **Nuclear and biomass sit at 0.85 to 0.91**, and the line barely moves. These plants are expensive to start and stop, so they run continuously and sell whatever the market pays. Steady output is the whole model.
- **Gas plants sit at 0.53 to 0.72.** They can ramp up and down quickly, so they follow demand, running hard in the evening peak and backing off overnight. The mid-range number is what "flexible" looks like in the data.
- **Offshore wind lands near 0.38.** Nothing is wrong here. Wind runs when the wind blows, and roughly 30 to 45 percent of the time is normal for the technology.
- **Batteries and peaking plants held by trading houses come in at 0.12 to 0.22.** They exist to fire during short, expensive windows. Running rarely is the strategy, not a failure.
One metric, applied across a whole market, tells you which business a company is actually in.
 
### Average achieved price reveals *when* a company generates, not just how much
 
Wholesale electricity prices change every half hour and can swing by a factor of two within a single day. Generating a megawatt hour at 6pm is worth considerably more than generating one at 4am.
 
Dividing each operator's estimated market value by its volume gives the average price per unit its output actually fetched. That single number captures timing:
 
- Flexible gas comes out high, because it deliberately runs into the expensive periods.
- Baseload comes out mid, because it generates just as much at 4am as at 6pm and averages across both.
- One trading party came out noticeably low, and the reason was checkable rather than assumed. Querying its output by half hour showed volume concentrated in the midday window, when solar pushes prices down. On one day those periods went outright negative, meaning generators were paying to keep running rather than being paid.
Two companies can produce identical volumes and earn very different amounts. This is the metric that makes that visible.
 
### No single company dominates, and concentration shifts across the day
 
Market concentration is measured with a Herfindahl index, which squares each company's share of total output and sums the results. If one firm produced everything the score would be 1.0. If output is spread thinly across many firms it approaches zero.
 
GB generation scores around 0.04 to 0.05, which is a genuinely competitive market. That may be counterintuitive if you expect a handful of giants to run the grid.
 
More interesting is that the score moves predictably with time of day. It rises overnight, when only a lean baseload fleet is running and output sits in a few hands, and falls during the day as a much wider range of plant is dispatched. The market's structure is not fixed. It changes hour by hour with demand.
 
---
 
## Architecture
 
```
Elexon Insights API (no key required)
        │
        ▼
Python ingestion ──▶ data/bronze/  (parquet, partitioned by settlement date)
        │
        ▼
dbt on DuckDB
   staging ──▶ intermediate ──▶ marts        + schema and data tests
        │
        ▼
publishing ──▶ Google Sheet ──▶ Tableau Public
```
 
Orchestrated by GitHub Actions on a daily cron. The runner starts empty each time, rebuilds the environment from `requirements.txt`, pulls a rolling window from the API, and publishes. Nothing large is persisted in the repo, because the API is the source of truth and ingestion is idempotent.
 
### Layers
 
| Layer | What it holds |
|---|---|
| **Bronze** (`data/bronze/`) | Raw API responses as parquet, partitioned by settlement date. Faithful to source, untyped. |
| **Staging** (`dbt/models/staging/`) | One model per source. Types cast, columns renamed, deduplicated, dead price providers filtered out. |
| **Intermediate** (`dbt/models/intermediate/`) | The unit-to-operator join. Every generation reading gains a company, a fuel type, and a registered capacity. |
| **Marts** (`dbt/models/marts/`) | Business-level aggregates, materialised as tables. |
 
This is the medallion pattern under dbt's naming conventions: bronze is the raw parquet, silver is staging plus intermediate, gold is the marts.
 
### Data sources
 
All from `https://data.elexon.co.uk/bmrs/api/v1/`. No API key.
 
| Dataset | Provides | Grain |
|---|---|---|
| `/reference/bmunits/all` | Unit register: lead party (the company), fuel type, registered capacity | One row per unit |
| `B1610` | Actual generation output | Per unit, per settlement period |
| `MID` | Market index price (wholesale reference) | Per settlement period, national |
 
### Marts
 
| Mart | Grain | Purpose |
|---|---|---|
| `mart_operator_period` | date × period × operator | Output, active units, running capacity, load factor |
| `mart_fuel_mix` | date × period × operator × fuel | Generation by technology |
| `mart_national_period` | date × period | National totals and market concentration (HHI) |
| `mart_operator_revenue` | date × period × operator | Output valued at the period's market price |
| `mart_operator_daily` | date × operator | Daily rollup. Small enough to publish to Sheets |
 
---
 
## Engineering decisions worth explaining
 
**The join key is not the obvious one.** `B1610` carries two unit identifiers. The National Grid one looks cleaner at first glance, matching 100% of the rows that have it, but it is null on roughly two thirds of records. The Elexon identifier is fully populated, so that is what the join uses. An inner join against the unit register then filters out supplier and demand units automatically, since they do not appear in a generation register. This is deliberate rather than incidental.
 
**Restatements are handled, not ignored.** Elexon revises settlement values across multiple runs over days and weeks. The staging layer deduplicates on `(settlement_date, settlement_period, bm_unit)` keeping the most recently ingested value, and the ingestion deliberately re-pulls a trailing window on every run so revisions are captured. The window is wide because `B1610` publishes with a lag of several days, a naive "pull today" pipeline finds nothing at all.
 
**Writes are idempotent.** Each settlement date owns a partition file, which is rewritten rather than appended. Running the same date twice produces identical output. The publishing step merges on the same key so a restated value replaces its predecessor rather than duplicating it.
 
**Polling, not streaming.** Elexon offers a push service (IRIS) that would deliver data the moment it publishes. It is not used here, because consuming a push stream needs an always-on subscriber and therefore paid hosting, and because the publishing tier refreshes roughly daily anyway. The API is already faster than the dashboard can consume. A genuinely event-driven version would be the next step if the refresh constraint were lifted.
 
---
 
## What the tests caught
 
The dbt test suite is not decoration. Three real problems surfaced through it or through sanity-checking outputs against how the grid actually behaves.
 
**Energy versus power.** Load factor was capped at exactly 0.50 across every operator, which is impossible, nuclear runs near 100% of capacity when it runs at all. The cause was that `B1610`'s `quantity` is **energy delivered in the half hour (MWh)**, not average power (MW). Dividing MWh by a MW capacity rating halves every result. Average MW is `quantity × 2`. After the fix a nuclear unit reads 0.99 rather than 0.49, and an automated range test now guards against the error returning.
 
**Load factor does not apply to aggregators.** After that fix, a handful of operators showed load factors above 5. These were demand-response aggregators, which orchestrate many small independent third-party sites rather than owning plant. Their registered capacity is not a fixed physical nameplate, availability is variable and contractual, so there is no meaningful denominator. The metric is nulled for these rather than reported, and the reasoning is documented. Choosing not to compute a number is sometimes the correct answer.
 
**Wholesale prices go negative.** A range test asserting prices are non-negative failed. The values were real: when supply exceeds demand, typically on windy or sunny midday periods, the market clears below zero because it is cheaper for some plant to pay to keep running than to shut down and restart. The test bounds were widened to permit real market behaviour rather than the data being "corrected".
 
---
 
## Running it
 
```bash
# environment
conda create -n gb-gen python=3.12 -y
conda activate gb-gen
pip install -r requirements.txt
 
# ingest a date range
python -m ingestion.ingest_reference
python -m ingestion.ingest_facts  --from 2026-07-01 --to 2026-07-15
python -m ingestion.ingest_prices --from 2026-07-01 --to 2026-07-15
 
# or a rolling window, which is what CI uses
python -m ingestion.ingest_facts --lookback-days 25
 
# transform and test
cd dbt
dbt deps  --profiles-dir .
dbt build --profiles-dir .
 
# publish
cd ..
python -m publishing.export_for_tableau        # CSVs to data/exports/
python -m publishing.export_to_sheets          # needs GCP_SA_KEY and SHEET_ID
```
 
The Google Sheets export authenticates from a service account JSON supplied through the `GCP_SA_KEY` environment variable, stored as a GitHub secret in CI. No credential is ever written to the repo.
 
---
 
## Current state
 
Honest about where this is.
 
**Working**
 
- Ingestion for all three datasets, idempotent, with both backfill and rolling-window modes
- Full dbt transformation layer, five marts, 22 passing tests
- GitHub Actions running the whole pipeline unattended on a daily schedule
- Publishing to Google Sheets with history accumulating across runs
- Tableau Public connected to the Sheet and refreshing automatically
**In progress**
 
- **The dashboard is unfinished.** Several worksheets exist (operator output, load factor, fuel mix through the day with an interactive view-mode toggle) but they are not yet assembled into a coherent dashboard, and the storyboard has not been built.
- **History is shallow.** Accumulation in the published Sheet was added recently, so the visible window is short and will deepen as the pipeline runs.
**Known technical debt**
 
- Bronze parquet paths in the staging models are written relative to the dbt project directory. This works because dbt is always invoked from there, but it has broken twice when another process read the same models. These should be anchored to the repository root rather than relying on the working directory.
- Ingesting `B1610` costs 48 API calls per day because the endpoint requires a settlement period. Elexon exposes bulk stream endpoints that would reduce this substantially. An early attempt timed out and the simple loop was kept to avoid stalling on it, but it is worth revisiting now the pipeline is stable.
- A `mart_restatements` model, surfacing rows whose settlement value changed between ingests, is designed but not built. It needs accumulated history to be meaningful.
- The publishing step writes the daily mart only. The half-hourly marts remain local, so the fuel-mix and national-context views cannot yet refresh live.
---
 
## Limitations
 
**Estimated market value is not revenue.** Output is valued at the wholesale market index price for each settlement period. Generators do not, in general, sell at spot. Most sell forward through power purchase agreements and hedges, and low-carbon plant sells under Contracts for Difference at a fixed strike price. Offshore wind under a CfD pays money back when spot runs above its strike, so spot valuation can overstate it substantially. The figure is a consistent, transparent, public-data measure of what generation was worth at market rates. It is not any operator's profit and loss.
 
**Lead party is not always the asset owner.** Elexon registers units to a lead party, which is sometimes the owner and sometimes a route-to-market or trading counterparty acting on their behalf. Company-level totals should be read as "volume registered to this party", not "volume generated by plant this party owns".
 
**Unclassified volume is bucketed, not resolved.** Around a fifth of volume belongs to units with no fuel type in the register. These are predominantly trading and aggregation parties. They are labelled as such rather than dropped or forced into a technology category, but the label characterises the dominant content and may include a small number of untagged physical units.
 
**Interconnector flows are imports, not GB generation.** They are handled as their own category and excluded from the physical-fuel view.
 
---
 
## Attribution
 
Contains data from Elexon's Insights Solution (BMRS). Use is governed by the BMRS Data Licence Terms and the BMRS API Terms of Use Policy. Non-commercial and academic use is permitted with acknowledgement of the source.
