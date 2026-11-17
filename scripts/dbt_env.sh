# source scripts/dbt_env.sh — point local dbt / scripts at the workspace with a short-lived OAuth token.
# Host comes from ~/.databrickscfg (DEFAULT profile); only `auth token` and `warehouses list` hit the API.
export PATH=$HOME/.local/bin:$PATH
export DBT_HOST=$(python3 -c 'import configparser,os;c=configparser.ConfigParser();c.read(os.path.expanduser("~/.databrickscfg"));print(c["DEFAULT"]["host"].removeprefix("https://").rstrip("/"))')
export DBT_TOKEN=$(databricks auth token -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
export DBT_HTTP_PATH=/sql/1.0/warehouses/$(databricks warehouses list -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
export DBT_SCHEMA=${DBT_SCHEMA:-dev_$(python3 -c 'import sys,json,base64;p=sys.argv[1].split(".")[1];print(json.loads(base64.urlsafe_b64decode(p+"="*(-len(p)%4)))["sub"].split("@")[0])' "$DBT_TOKEN")_tenderlens}
