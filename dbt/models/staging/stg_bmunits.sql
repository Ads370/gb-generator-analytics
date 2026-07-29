-- Staging step: BM unit reference. One row per BM unit, with its lead party (the operator).
with source as (
    select 
        "elexonBmUnit" as elexon_bm_unit,
        "nationalGridBmUnit" as national_grid_bm_unit,
        "leadPartyName" as lead_party_name,
        "leadPartyId" as lead_party_id,
        "fuelType" as fuel_type,
        "bmUnitType" as bm_unit_type,
        cast("generationCapacity" as double) as generation_capacity,
        cast("demandCapacity" as double) as demand_capacity,
        "interconnectorId" as interconnector_id,
        ingested_at
    from read_parquet('../data/bronze/bmunits/bmunits.parquet')
    where "elexonBmUnit" is not null
),

deduped as(
    select*,
        row_number() over (
            partition by elexon_bm_unit
            order by ingested_at desc
        ) as rn
    from source
)

select
    elexon_bm_unit,
    national_grid_bm_unit,
    lead_party_name,
    lead_party_id,
    fuel_type,
    bm_unit_type,
    generation_capacity,
    demand_capacity,
    interconnector_id,
    ingested_at
from deduped
where rn = 1