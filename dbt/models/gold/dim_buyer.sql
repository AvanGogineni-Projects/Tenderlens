-- One row per buying organisation.
select
    buyer_key,
    mode(buyer_name) as name,
    mode(buyer_country) as country,
    count(*) as awards,
    count(distinct supplier_key) as suppliers,
    sum(value_eur) as value_eur,
    avg(tenders_received) as avg_tenders_received,
    min(award_date) as first_award,
    max(award_date) as last_award
from {{ ref('fct_awards') }}
where buyer_key is not null
group by buyer_key
