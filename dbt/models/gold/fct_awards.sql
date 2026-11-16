-- One row per (notice, lot, winning organisation), in the buyer's currency and in EUR.
with lots as (
    select * from {{ source('silver', 'silver_lots') }}
),
orgs as (
    select * from {{ ref('stg_organisations') }}
),
joined as (
    select
        w.publication_number,
        w.lot_id,
        w.org_ref,
        n.notice_id,
        n.procedure_id,
        n.publication_date,
        coalesce(w.award_date, w.signed_date, n.publication_date) as award_date,
        case when w.award_date is not null then 'award' when w.signed_date is not null then 'signed'
             else 'published' end as award_date_basis,
        coalesce(l.title, n.title) as title,
        coalesce(l.main_cpv, n.main_cpv) as cpv,
        left(coalesce(l.main_cpv, n.main_cpv), 2) as cpv_division,
        coalesce(l.contract_nature, n.contract_nature) as contract_nature,
        n.procedure_type,
        l.framework,
        b.org_key as buyer_key,
        b.name as buyer_name,
        b.country as buyer_country,
        s.org_key as supplier_key,
        s.name as supplier_name,
        s.country as supplier_country,
        s.swedish_orgnr as supplier_swedish_orgnr,
        s.size as supplier_size,
        s.is_natural_person as supplier_is_person,
        w.tenders_received,
        w.shared_tender,
        w.tender_value as value,
        w.tender_currency as currency,
        n.awarded_total as notice_total,
        n.awarded_currency as notice_total_currency,
        l.start_date,
        l.end_date,
        l.duration_value,
        l.duration_unit
    from {{ ref('stg_winners') }} w
    join {{ ref('stg_notices') }} n using (publication_number)
    join orgs s on s.publication_number = w.publication_number and s.org_ref = w.org_ref
    left join orgs b on b.publication_number = w.publication_number and b.org_ref = element_at(n.buyer_refs, 1)
    left join lots l on l.publication_number = w.publication_number and l.lot_id = w.lot_id
)
, converted as (
    select
        j.*,
        cast(case when j.currency = 'EUR' then j.value else j.value / fx.per_eur end as double) as raw_value_eur
    from joined j
    left join {{ ref('fx_monthly') }} fx
        -- rate of the award month, clamped to the seed's range (award dates can predate it or be typos)
        on fx.currency = j.currency
       and fx.month = trunc(least(greatest(j.award_date, date'2023-01-01'), j.publication_date), 'MM')
),
flagged as (
    select
        *,
        -- typos (cents as units, extra zeros): over EUR 5bn for one award, or, for an ordinary contract,
        -- more than twice the notice's own total. Frameworks are exempt from the second check: each
        -- supplier reports the framework ceiling, which legitimately exceeds the notice total.
        -- The raw value stays; value_eur is left empty so totals aren't distorted.
        coalesce(raw_value_eur > 5e9
                 or (coalesce(framework, 'none') = 'none' and notice_total_currency = currency
                     and value > 2 * notice_total and notice_total > 0),
                 false) as value_suspect
    from converted
)
select
    concat_ws('|', j.publication_number, j.lot_id, j.org_ref) as award_id,
    j.* except (raw_value_eur),
    case when not j.value_suspect then j.raw_value_eur end as value_eur,
    -- end of contract: reported end date, else start (or award) + duration
    -- (durations over 50 years are typos and would overflow date arithmetic)
    coalesce(j.end_date, case
        when j.duration_unit = 'MONTH' and j.duration_value between 1 and 600
            then add_months(coalesce(j.start_date, j.award_date), j.duration_value)
        when j.duration_unit = 'YEAR' and j.duration_value between 1 and 50
            then add_months(coalesce(j.start_date, j.award_date), 12 * j.duration_value)
        when j.duration_unit = 'DAY' and j.duration_value between 1 and 18250
            then date_add(coalesce(j.start_date, j.award_date), j.duration_value)
    end) as expected_end
from flagged j
