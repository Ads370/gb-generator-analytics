--Mart. Operator period. One row per operator per settlement period.
--It rolls unit-level generation up to the operator level, and adds the operator's fuel type and capacity.
--The grain is one row per (settlement_date, settlement_period, lead_party_name)
with unit_level as (
    select
        settlement_date,
        settlement_period,
        lead_party_name,
        lead_party_id,
        bm_unit,
        quantity_mw,
        generation_capacity,
        fuel_type,
    from {{ ref('int_generation_operators') }}
    where quantity_mw > 0
)
--positive output only indicates that B1610 can carry small negative values for units
--drawing power. The generation is kept, the consumption noise is dropped.

select
    settlement_date,
    settlement_period,
    lead_party_name,
    lead_party_id,
    sum(quantity_mw) as total_output_mw,                        --output: MW averaged over a half-hour perido is MW; energy is MW * 0.5h
    sum(quantity_mw)*0.5 as total_output_mwh,                   
    count(distinct bm_unit) as active_units,                    --fleet actually running this period
    sum(distinct generation_capacity) as running_capacity_mw,   --registered capacity of the units running
    case                                                        --load factor: how hard the running fleet was pushed (0..1)
        when sum(distinct generation_capacity) > 0 
        then sum(quantity_mw)/sum(distinct generation_capacity)
    end as load_factor

from unit_level
group by
    settlement_date,
    settlement_period,
    lead_party_name,
    lead_party_id