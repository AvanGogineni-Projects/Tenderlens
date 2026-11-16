# source scripts/dbt_env.sh — point local dbt at the dev workspace with a short-lived OAuth token
export PATH=$HOME/.local/bin:$PATH
export DBT_HOST=$(databricks auth describe -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["details"]["host"].removeprefix("https://"))')
export DBT_HTTP_PATH=/sql/1.0/warehouses/$(databricks warehouses list -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
export DBT_TOKEN=$(databricks auth token -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
export DBT_SCHEMA=${DBT_SCHEMA:-dev_$(databricks current-user me -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["userName"].split("@")[0])')_tenderlens}
