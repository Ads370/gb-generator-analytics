--Mart. Estimated wholesale revenue per operator per settlement period.
--Output MWh is valued at the period's market index price.
--To Note: this is an estimate. Generators sell forward under PPAs, hedges, and CfDs, so spot price valuation is a public-data proxy,
--not actual earnings. Offshore wind under a CfD in particular does not earn a spot.
--This is a consistent, transparent valuation of output at market value using public data.(this is not the realised revenue/ACTUAL operator's proit&loss).
with operator_output as (
    select
        settlement_date,
        settlement_period,
        lead_party_name,
        total_output_mwh
    from{{ ref('mart_operator_period') }}
),

prices as (
    select
        settlement_date,
        settlement_period,
        price_gbp_per_mwh
    from {{ ref('stg_mid')}}

)

select
    o.settlement_date,
    o.settlement_period,
    o.lead_party_name,
    o.total_output_mwh,
    p.price_gbp_per_mwh,
    o.total_output_mwh * p.price_gbp_per_mwh as estimated_revenue_gbp
from operator_output o
inner join prices p
    on o.settlement_date = p.settlement_date
    and o.settlement_period = p.settlement_period