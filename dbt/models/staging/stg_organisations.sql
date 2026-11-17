-- Organisations with a stable key. Privacy: a Swedish ID whose third digit is 0 or 1 is a personal
-- identity number (that digit is the birth month), not an org number (always 2 or more), so it is a
-- private individual even when the sender didn't flag them as one: no name, no ID, never linked.
with o as (
    select
        o.*,
        -- coalesce: `false or null` is null, and a null flag would slip past both `not is_person` and
        -- `case when is_person` filters downstream
        coalesce(o.is_natural_person
            or (o.country = 'SWE' and substr({{ swedish_orgnr('o.company_id') }}, 3, 1) in ('0', '1')), false)
            as is_person
    from {{ source('silver', 'silver_organisations') }} o
)
select
    publication_number,
    org_ref,
    case when is_person then null else name end as name,
    case when is_person then null else company_id end as company_id,
    country,
    nuts,
    case when is_person then null else city end as city,
    size,
    is_person as is_natural_person,
    is_buyer,
    {{ org_key('country', 'company_id', 'name', 'is_person', 'publication_number', 'org_ref') }} as org_key,
    case when country = 'SWE' and not is_person then {{ swedish_orgnr('company_id') }} end as swedish_orgnr
from o
