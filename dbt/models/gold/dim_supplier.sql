-- One row per winning organisation, with its award history and, for Swedish companies, the Bolagsverket
-- register and Bolagsvakt's risk score.
with awards as (
    select * from {{ ref('fct_awards') }} where not supplier_is_person
),
per_supplier as (
    select
        supplier_key,
        mode(supplier_name) as name,
        mode(supplier_country) as country,
        max(supplier_swedish_orgnr) as swedish_orgnr,
        mode(supplier_size) as size,
        count(*) as awards,
        count(distinct buyer_key) as buyers,
        sum(value_eur) as value_eur,
        min(award_date) as first_award,
        max(award_date) as last_award
    from awards
    group by supplier_key
)
select
    s.*,
    r.registered_name,
    r.legal_form,
    r.deregistered_on,
    r.deregistration_reason,
    r.bankruptcy_probability,
    r.risk_times_average,
    r.in_proceedings
from per_supplier s
left join {{ ref('stg_register') }} r on r.org_nr = s.swedish_orgnr
