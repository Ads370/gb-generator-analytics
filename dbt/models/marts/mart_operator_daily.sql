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
),

daily as (
    select
        settlement_date,
        lead_party_name,
        lead_party_id,
        sum(total_output_mwh)    as daily_output_mwh,
        max(active_units)        as peak_active_units,
        max(running_capacity_mw) as peak_capacity_mw,
        avg(load_factor)         as avg_load_factor,
        max(load_factor)         as peak_load_factor,
        count(*)                 as active_periods
    from period_level
    group by settlement_date, lead_party_name, lead_party_id
),

revenue_daily as (
    select
        settlement_date,
        lead_party_name,
        sum(estimated_revenue_gbp) as daily_revenue_gbp
    from {{ ref('mart_operator_revenue') }}
    group by settlement_date, lead_party_name
),

generator_flag as (
    select
        lead_party_name,
        max(case
            when fuel_type not in ('TRADING/AGGREGATOR', 'UNCLASSIFIED', 'INTERCONNECTOR')
                 and fuel_type not like 'INT%'
            then 1 else 0
        end) as is_physical_generator
    from {{ ref('mart_fuel_mix') }}
    group by lead_party_name
)

select
    d.*,
    r.daily_revenue_gbp,
    case
        when d.daily_output_mwh > 0
        then r.daily_revenue_gbp / d.daily_output_mwh
    end as avg_price_achieved,
    coalesce(g.is_physical_generator, 0) as is_physical_generator
from daily d
left join revenue_daily r
    on  d.settlement_date  = r.settlement_date
    and d.lead_party_name  = r.lead_party_name
left join generator_flag g
    on  d.lead_party_name  = g.lead_party_name
