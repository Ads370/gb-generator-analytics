--Intermediate. The generation output is joined to operators.
--Every B1610 reading gains its lead party name, fuel type, and capacity.
--The inner join drops supplier and non-generation units (as they dont match
--the generation-unit reference table), leaving only attributable generation.
select
    gen.settlement_date,
    gen.settlement_period,
    gen.bm_unit,
    gen.national_grid_bm_unit,
    gen.quantity_mw,
    gen.half_hour_end_time,
    ref.lead_party_name,
    ref.lead_party_id,
    ref.fuel_type,
    ref.bm_unit_type,
    ref.generation_capacity,
    ref.interconnector_id,
    gen.ingested_at
from {{ ref('stg_b1610') }} as gen
inner join {{ ref('stg_bmunits') }} as ref
    on gen.bm_unit = ref.elexon_bm_unit
    

