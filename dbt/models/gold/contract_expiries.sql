-- Contracts ending in the next 18 months: the next tender for this work is likely coming.
select
    award_id,
    expected_end,
    buyer_key,
    buyer_name,
    buyer_country,
    supplier_key,
    supplier_name,
    cpv,
    cpv_division,
    title,
    value_eur,
    award_date,
    framework,
    case when end_date is not null then 'reported' else 'from_duration' end as end_basis
from {{ ref('fct_awards') }}
where expected_end between current_date() and add_months(current_date(), 18)
