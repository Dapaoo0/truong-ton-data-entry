import os, json
from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# We test fetching stage_logs with its related dim_lo
res = supabase.table("stage_logs").select("*, dim_lo(lo_name, area_ha, dim_doi(doi_name), dim_farm(farm_name))").limit(1).execute()
print(json.dumps(res.data, indent=2))
