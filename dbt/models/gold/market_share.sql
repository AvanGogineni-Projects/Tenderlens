-- Who wins each market: buyer country x CPV division x year, by value in EUR.
with by_supplier as (
    select
        buyer_country,
        cpv_division,
        year(award_date) as year,
        supplier_key,
        mode(supplier_name) as supplier_name,
        count(*) as awards,
        sum(value_eur) as value_eur
    from {{ ref('fct_awards') }}
    where value_eur > 0 and not supplier_is_person  -- a share of a zero-value market means nothing
    group by all
)
select
    *,
    value_eur / sum(value_eur) over (partition by buyer_country, cpv_division, year) as share,
    rank() over (partition by buyer_country, cpv_division, year order by value_eur desc) as rank
from by_supplier
