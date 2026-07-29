--Mart. Generation by operator and fuel type per settlement period.
--Grain. One row per (settlement_date, settlement_period, lead_party_name, fuel_type)
--Separate from mart_operator_period to keep that mart at a clean operatorgrain
with unit_level as (
    select
        settlement_date,
        settlement_period,
        lead_party_name,
        fuel_type,
        bm_unit,
        sum(quantity_mw) as unit_output_mwh   --quantity is MWh per half hour
    from {{ ref('int_generation_operators') }}
    where quantity_mw > 0
    group by 
        settlement_date,
        settlement_period,
        lead_party_name,
        fuel_type,
        bm_unit
)

select
    settlement_date,
    settlement_period,
    lead_party_name,
    case
        when fuel_type is not null then fuel_type
        when lead_party_name ilike '%market coupling%'
             or lead_party_name ilike '%interconnector%' then 'INTERCONNECTOR'
        else 'TRADING/AGGREGATOR'
    end as fuel_type,
    sum(unit_output_mwh)     as fuel_output_mwh,
    count(distinct bm_unit)  as active_units
from unit_level
group by
    settlement_date,
    settlement_period,
    lead_party_name,
    case
        when fuel_type is not null then fuel_type
        when lead_party_name ilike '%market coupling%'
             or lead_party_name ilike '%interconnector%' then 'INTERCONNECTOR'
        else 'TRADING/AGGREGATOR'
    end