import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class Settings:
    port = int(os.getenv("PORT") or "5050")
    mongo_uri = os.getenv("MONGODB_URI") or "mongodb://127.0.0.1:27017/notes_ai"
    client_url = os.getenv("CLIENT_URL") or "http://localhost:5173"
    jwt_secret = os.getenv("JWT_SECRET") or "dev-only-jwt-secret-change-me"
    encryption_key = os.getenv("ENCRYPTION_KEY") or "dev-only-encryption-key-change-me"
    google_client_id = os.getenv("GOOGLE_CLIENT_ID") or ""
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or ""
    google_callback_url = os.getenv("GOOGLE_CALLBACK_URL") or "http://localhost:5050/api/auth/google/callback"
    github_client_id = os.getenv("GITHUB_CLIENT_ID") or ""
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET") or ""
    github_callback_url = os.getenv("GITHUB_CALLBACK_URL") or "http://localhost:5050/api/auth/github/callback"
    github_token = os.getenv("GITHUB_TOKEN") or ""
    gemini_api_key = os.getenv("GEMINI_API_KEY") or ""
    gemini_model = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite"
    is_production = (os.getenv("ENV") or os.getenv("NODE_ENV") or "") == "production"


settings = Settings()


def public_config():
    google = bool(settings.google_client_id and settings.google_client_secret)
    return {
        "google": google,
        "github": bool(settings.github_client_id and settings.github_client_secret),
        "gemini": bool(settings.gemini_api_key),
        "devLogin": (not google) and (not settings.is_production),
    }
