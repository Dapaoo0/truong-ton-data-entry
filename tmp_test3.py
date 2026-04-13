import os, json
from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
query = supabase.table("base_lots").select("*, dim_lo!inner(lo_name, area_ha, dim_doi!inner(doi_name), dim_farm!inner(farm_name))").eq("is_deleted", False)
res = query.limit(1).execute()
print(json.dumps(res.data, indent=2))
