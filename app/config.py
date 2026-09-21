import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def open_stores():
    from app.library_db import LibraryDb
    from app.memory import RunStore

    store = RunStore()
    db = LibraryDb()
    return store, db


def make_providers(mock: bool, slow: float = 0.0) -> dict:
    if mock:
        from app.providers import demo_providers
        return demo_providers(slow)

    from app.providers import GeminiProvider
    gemini = GeminiProvider(GEMINI_MODEL)
    return {"supervisor": gemini, "catalogue": gemini, "desk": gemini}