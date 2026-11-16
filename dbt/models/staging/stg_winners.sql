-- One row per (notice, lot, winning organisation).
-- Silver keeps the source's shape: one row per tender x tenderer. Each tender's value is split evenly
-- between the party's members: a sole bidder keeps it all, a 3-company consortium gets a third each, and
-- when a sender puts every framework supplier in one "tendering party" that all tenders point at
-- (e.g. 4458-2025: 82 suppliers, 6,724 rows), each supplier gets one row worth the average tender.
with winning as (
    select
        a.*,
        count(*) over (partition by a.publication_number, a.tender_id) as tenderers_on_tender
    from {{ source('silver', 'silver_awards') }} a
    join {{ ref('stg_notices') }} n using (publication_number)
    where a.is_winner and a.org_ref is not null
)
select
    publication_number,
    lot_id,
    org_ref,
    count(distinct tender_id) as tenders,
    -- party value split evenly between members; double for the division (decimal / count keeps ~20
    -- decimal places and overflows on large amounts), stored back as an exact decimal
    try_cast(sum(cast(tender_value as double) / tenderers_on_tender) as decimal(22, 2)) as tender_value,
    max(tender_currency) as tender_currency,
    min(award_date) as award_date,
    min(signed_date) as signed_date,
    max(tenders_received) as tenders_received,
    max(tenderers_on_tender) > 1 as shared_tender
from winning
group by publication_number, lot_id, org_ref
