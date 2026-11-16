-- Bolagsverket register and Bolagsvakt risk scores (uploaded from Bolagsvakt; companies only, no persons).
select
    c.org_nr,
    c.name as registered_name,
    c.legal_form,
    c.registered_on,
    c.deregistered_on,
    c.deregistration_reason,
    r.probability as bankruptcy_probability,
    r.times_average as risk_times_average,
    r.in_proceedings,
    r.filed_on as last_report_filed_on
from {{ register_file('companies') }} c
left join {{ register_file('risk_scores') }} r using (org_nr)
