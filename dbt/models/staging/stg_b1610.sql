--Staging. Step: B1610. One row per settlement period, with all the B1610 data for that settlement period.
--Deduplicates to the latest-ingested value per (date, period, unit),
--resolving Elexon's settlement-run restatements. B1610 exposes no publish timestamp,
--so ingested_at is the freshenss signal.

with source as (
    select
        "settlementDate" as settlement_date,
        "settlementPeriod" as settlement_period,
        "bmUnit" as bm_unit,
        "nationalGridBmUnitId" as national_grid_bm_unit,
        cast("quantity" as double) as quantity_mw,
        "psrType" as psr_type,
        "halfHourEndTime" as half_hour_end_time,
        ingested_at
    from read_parquet('../data/bronze/b1610/**/*.parquet')
),

ranked as (
    select *,
        row_number() over (
            partition by settlement_date, settlement_period, bm_unit
            order by ingested_at desc
        ) as rn
    from source
)

select
    settlement_date,
    settlement_period,
    bm_unit,
    national_grid_bm_unit,
    quantity_mw,
    psr_type,
    half_hour_end_time,
    ingested_at
from ranked
where rn = 1