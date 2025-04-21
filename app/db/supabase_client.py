from supabase import create_client
from app.core import config

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
