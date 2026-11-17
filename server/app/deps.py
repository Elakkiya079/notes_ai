from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, Request

from app import db as database
from app.lib.tokens import verify_session


def current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        payload = verify_session(token)
        return database.db.users.find_one({"_id": ObjectId(payload["uid"])})
    except (InvalidId, Exception):
        return None


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user
