select
    o.*,
    {{ org_key('o.country', 'o.company_id', 'o.name', 'o.is_natural_person', 'o.publication_number', 'o.org_ref') }} as org_key,
    case when o.country = 'SWE' and not o.is_natural_person then {{ swedish_orgnr('o.company_id') }} end as swedish_orgnr
from {{ source('silver', 'silver_organisations') }} o
