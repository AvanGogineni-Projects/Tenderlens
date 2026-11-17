-- Privacy: no Swedish personal identity number (third digit 0/1) survives as an org number or name holder.
select org_key from {{ ref('stg_organisations') }}
where swedish_orgnr is not null and substr(swedish_orgnr, 3, 1) in ('0', '1')
union all
select supplier_key from {{ ref('dim_supplier') }}
where swedish_orgnr is not null and substr(swedish_orgnr, 3, 1) in ('0', '1')
