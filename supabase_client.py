import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


# Folder containing supabase_client.py
BASE_DIR = Path(__file__).resolve().parent

# Load the .env file from the same folder
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL is missing from the .env file."
    )

if not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_ANON_KEY is missing from the .env file."
    )

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)
