--Mart. National grid picture per settlement period.
--One row per settlement period: the total generation and market concentration.
--It provides dashboard context (the performance of the whole grid) above the operator-level drilldowns.
with operator_period as (
    select
        settlement_date,
        settlement_period,
        lead_party_name,
        total_output_mwh
    from{{ ref('mart_operator_period')}}
),

national_total as (
    select
        settlement_date,
        settlement_period,
        sum(total_output_mwh) as national_output_mwh,
        count(distinct lead_party_name) as active_operators
    from operator_period
    group by settlement_date, settlement_period
),

                                                                               --each operator's share of national output on that period, squared for HHI
operator_shares as(
    select
        op.settlement_date,
        op.settlement_period,
        pow(op.total_output_mwh / nt.national_output_mwh, 2) as share_squared
    from operator_period op
    inner join national_total nt
        on op.settlement_date = nt.settlement_date
        and op.settlement_period = nt.settlement_period
    where nt.national_output_mwh > 0
),                                                

concentration as (
    select
        settlement_date,
        settlement_period,
        sum(share_squared) as hhi
    from operator_shares
    group by settlement_date, settlement_period
)

select 
    nt.settlement_date,
    nt.settlement_period,
    nt.national_output_mwh,
    nt.active_operators,
    con.hhi
from national_total as nt
inner join concentration con
    on nt.settlement_date = con.settlement_date
    and nt.settlement_period = con.settlement_period

