{# Swedish org number (10 digits) from the ways senders write it: 556123-4567, SE5561234567(01), 16556123-4567. #}
{% macro swedish_orgnr(company_id) -%}
case
  when length(regexp_replace({{ company_id }}, '[^0-9]', '')) = 10 then regexp_replace({{ company_id }}, '[^0-9]', '')
  when length(regexp_replace({{ company_id }}, '[^0-9]', '')) = 12 and upper({{ company_id }}) like 'SE%'
    then substr(regexp_replace({{ company_id }}, '[^0-9]', ''), 1, 10)
  when length(regexp_replace({{ company_id }}, '[^0-9]', '')) = 12 and regexp_replace({{ company_id }}, '[^0-9]', '') like '16%'
    then substr(regexp_replace({{ company_id }}, '[^0-9]', ''), 3, 10)
end
{%- endmacro %}

{# One key per real organisation across notices: country + normalised registration id, else country + name.
   Natural persons get a per-notice key so they are never linked across notices. #}
{% macro org_key(country, company_id, name, is_natural_person, publication_number, org_ref) -%}
case
  when {{ is_natural_person }} then concat('person:', {{ publication_number }}, ':', {{ org_ref }})
  when {{ country }} = 'SWE' and {{ swedish_orgnr(company_id) }} is not null
    then concat('SWE:', {{ swedish_orgnr(company_id) }})
  when length(regexp_replace(upper(coalesce({{ company_id }}, '')), '[^0-9A-Z]', '')) >= 5
    then concat(coalesce({{ country }}, '?'), ':', regexp_replace(upper({{ company_id }}), '[^0-9A-Z]', ''))
  else concat(coalesce({{ country }}, '?'), ':name:', lower(trim(regexp_replace({{ name }}, '\\s+', ' '))))
end
{%- endmacro %}

{% macro register_file(name) -%}
read_files('/Volumes/{{ target.catalog }}/{{ target.schema }}/raw/bolagsvakt/{{ name }}.parquet', format => 'parquet')
{%- endmacro %}
