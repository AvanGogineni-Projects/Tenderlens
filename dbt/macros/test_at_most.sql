{% test at_most(model, column_name, max_value) %}
select * from {{ model }} where {{ column_name }} > {{ max_value }}
{% endtest %}
