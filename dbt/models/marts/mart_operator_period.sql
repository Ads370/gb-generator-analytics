--Mart. Operator period. One row per operator per settlement period.
--It rolls unit-level generation up to the operator level, and adds the operator's fuel type and capacity.
--The grain is one row per (settlement_date, settlement_period, lead_party_name)
with unit_level as (
    select                                            --one row per unit per period. output and single capacity
        settlement_date,
        settlement_period,
        lead_party_name,
        lead_party_id,
        bm_unit,
        sum(quantity_mw) as unit_output_mwh,
        max(generation_capacity) as unit_capacity_mw
    from {{ ref('int_generation_operators') }}
    where quantity_mw > 0
    group by
        settlement_date,
        settlement_period,
        lead_party_name,
        lead_party_id,
        bm_unit
),

operator_level as (
    select                                             --roll units up to operator. capacity sums per-unit, not per-value
        settlement_date,
        settlement_period,
        lead_party_name,
        lead_party_id,
        sum(unit_output_mwh) as total_output_mwh,
        sum(unit_output_mwh)*2 as total_output_mw,     --avg power over the half hour
        count(distinct bm_unit) as active_units,
        sum(unit_capacity_mw) as running_capacity_mw
    from unit_level
    group by
        settlement_date,
        settlement_period,
        lead_party_name,
        lead_party_id
)

select *,
    case
        when running_capacity_mw > 0
            and (total_output_mw / running_capacity_mw) <= 1.5
        then total_output_mw / running_capacity_mw
    end as load_factor
from operator_level

