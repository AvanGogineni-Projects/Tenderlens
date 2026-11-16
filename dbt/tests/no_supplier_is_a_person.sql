-- Privacy: natural persons never reach the supplier dimension.
select * from {{ ref('dim_supplier') }} where supplier_key like 'person:%'
