import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Get the folder where this file lives
BASE_DIR = Path(__file__).resolve().parent

# Force load the .env file from this folder
env_path = BASE_DIR / ".env"

print("Loading .env from:", env_path)  # Debug line

load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

print("URL:", SUPABASE_URL)  # Debug
print("KEY exists:", bool(SUPABASE_ANON_KEY))  # Debug

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)