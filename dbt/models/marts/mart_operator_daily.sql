-- Mart. Operator performance aggregated to a daily grain.
-- The grain consists in one row per (settlement-date, lead_party_name).
-- This granularity is small enough to publish to Google Sheets for Tableau public daily refresh.
with period_level as (
    select
        settlement_date,
        lead_party_name,
        lead_party_id,
        total_output_mwh,
        total_output_mw,
        active_units,
        running_capacity_mw,
        load_factor
    from {{ ref('mart_operator_period') }}
)

select 
    settlement_date,
    lead_party_name,
    lead_party_id, 
    sum(total_output_mwh) as daily_output_mwh, --energy sums across the selected day
    max(active_units) as peak_active_units, 
    max(running_capacity_mw) as peak_capacity_mw, --Fleet peak units running at any point and peak capacity available
    avg(load_factor) as avg_load_factor,
    max(load_factor) as peak_load_factor, --those two metrics indicate the utilization across the day (nulls fro unreliable-capcity rows are ignored)
    count(*) as active_periods --number of periods the operator generated in (out of 48)
from period_level
group by
    settlement_date,
    lead_party_name,
    lead_party_id
