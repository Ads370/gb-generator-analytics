-- Staging step: BM unit reference. One row per BM unit, with its lead party (the operator).

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