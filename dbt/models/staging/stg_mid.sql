--Staging. MID market index (wholesale ref. price) per settlement period.
--Filters to APXMIDP (live provider). N2EXMIDP stopped reporting and returns zeros. One row per (settlement_date, settlement_period).
select
    "settlementDate" as settlement_date,
    "settlementPeriod" as settlement_period,
    "dataProvider" as data_provider,
    cast("price" as double) as price_gbp_per_mwh,
    cast("volume" as double) as traded_volume_mwh,
    ingested_at
from read_parquet('../data/bronze/mid/**/*.parquet')
where "dataProvider" = 'APXMIDP'
