-- Shares within each market add up to 1.
select buyer_country, cpv_division, year, sum(share) as total
from {{ ref('market_share') }}
group by all
having abs(sum(share) - 1) > 1e-6
