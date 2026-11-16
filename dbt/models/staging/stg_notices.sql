-- Current version of each notice: drop a notice once a later change notice replaces it. Senders point at the
-- replaced notice by publication number, notice id, or notice id + version: three exact-match anti-joins
-- (one `IN (a, b, c)` condition can't use a hash join and compares every notice with every change).
with replaced as (
    select distinct changed_notice as k from {{ source('silver', 'silver_notices') }} where changed_notice is not null
)
select n.*
from {{ source('silver', 'silver_notices') }} n
left anti join replaced by_publication on by_publication.k = n.publication_number
left anti join replaced by_id on by_id.k = n.notice_id
left anti join replaced by_version on by_version.k = concat(n.notice_id, '-', n.version)
