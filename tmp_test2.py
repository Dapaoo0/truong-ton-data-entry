import os, json
from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
query = supabase.table("stage_logs").select("*, dim_lo!inner(lo_name, area_ha, dim_doi(doi_name), dim_farm!inner(farm_name))").eq("is_deleted", False)
query = query.eq("dim_lo.dim_farm.farm_name", "Farm 157")
res = query.limit(1).execute()
print(json.dumps(res.data, indent=2))
