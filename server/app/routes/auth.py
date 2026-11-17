from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import public_config, settings
from app import db as database
from app.deps import current_user
from app.lib.crypto import encrypt
from app.lib.tokens import sign_session, sign_state, verify_state

router = APIRouter()


def public_user(user):
    return {
        "id": str(user["_id"]),
        "name": user.get("name") or "Reader",
        "email": user.get("email") or "",
        "avatar": user.get("avatar") or "",
        "github": {"username": user["githubUsername"]} if user.get("githubUsername") else None,
    }


def session_cookie(response, user):
    response.set_cookie(
        "token",
        sign_session(user["_id"]),
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def _redirect_error(code):
    return RedirectResponse(f"{settings.client_url}/?auth={code}", status_code=302)


@router.get("/api/auth/config")
def auth_config():
    return public_config()


@router.get("/api/auth/me")
def me(user=Depends(current_user)):
    return {"user": public_user(user) if user else None}


@router.post("/api/auth/dev")
def dev_login():
    if not public_config()["devLogin"]:
        raise HTTPException(status_code=403, detail="Local preview is only available before Google sign-in is configured.")
    now = datetime.now(timezone.utc)
    user = database.db.users.find_one({"googleId": "dev-local"})
    if not user:
        inserted = database.db.users.insert_one(
            {
                "googleId": "dev-local",
                "email": "local@notes.dev",
                "name": "Local preview",
                "avatar": "",
                "githubId": "",
                "githubUsername": "",
                "githubAccessToken": "",
                "createdAt": now,
                "updatedAt": now,
            }
        )
        user = database.db.users.find_one({"_id": inserted.inserted_id})
    response = JSONResponse({"user": public_user(user)})
    session_cookie(response, user)
    return response


@router.post("/api/auth/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("token", path="/")
    return response


@router.get("/api/auth/google")
def google_start():
    if not settings.google_client_id or not settings.google_client_secret:
        return _redirect_error("google_not_configured")
    from urllib.parse import urlencode

    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": sign_state({"purpose": "google"}),
            "prompt": "select_account",
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302)


@router.get("/api/auth/google/callback")
def google_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return _redirect_error("google_denied")
    try:
        payload = verify_state(state)
        if payload.get("purpose") != "google":
            return _redirect_error("google_error")
    except Exception:
        return _redirect_error("google_error")
    if not code:
        return _redirect_error("google_error")

    import httpx

    token_response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_callback_url,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if token_response.status_code >= 400:
        return _redirect_error("google_error")
    access_token = token_response.json().get("access_token")
    profile_response = httpx.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if profile_response.status_code >= 400:
        return _redirect_error("google_error")
    profile = profile_response.json()
    if not profile.get("sub"):
        return _redirect_error("google_error")

    now = datetime.now(timezone.utc)
    user = database.db.users.find_one({"googleId": profile["sub"]})
    if not user:
        inserted = database.db.users.insert_one(
            {
                "googleId": profile["sub"],
                "email": profile.get("email") or "",
                "name": profile.get("name") or profile.get("email") or "Reader",
                "avatar": profile.get("picture") or "",
                "githubId": "",
                "githubUsername": "",
                "githubAccessToken": "",
                "createdAt": now,
                "updatedAt": now,
            }
        )
        user = database.db.users.find_one({"_id": inserted.inserted_id})
    else:
        database.db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "email": profile.get("email") or user.get("email") or "",
                    "name": profile.get("name") or user.get("name") or "Reader",
                    "avatar": profile.get("picture") or user.get("avatar") or "",
                    "updatedAt": now,
                }
            },
        )
        user = database.db.users.find_one({"_id": user["_id"]})
    response = RedirectResponse(f"{settings.client_url}/notes", status_code=302)
    session_cookie(response, user)
    return response


@router.get("/api/auth/github")
def github_start(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(settings.client_url + "/", status_code=302)
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured on the server.")
    from urllib.parse import urlencode

    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_callback_url,
            "scope": "repo",
            "state": sign_state({"purpose": "github", "uid": str(user["_id"])}),
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}", status_code=302)


@router.get("/api/auth/github/callback")
def github_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"{settings.client_url}/import?github=denied", status_code=302)
    try:
        payload = verify_state(state)
    except Exception:
        return RedirectResponse(f"{settings.client_url}/import?github=error", status_code=302)
    if payload.get("purpose") != "github" or not payload.get("uid") or not code:
        return RedirectResponse(f"{settings.client_url}/import?github=error", status_code=302)

    import httpx

    token_response = httpx.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_callback_url,
        },
        headers={"Accept": "application/json"},
        timeout=30,
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    if token_response.status_code >= 400 or not access_token:
        return RedirectResponse(f"{settings.client_url}/import?github=error", status_code=302)

    profile_response = httpx.get(
        "https://api.github.com/user",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "notes-ai",
        },
        timeout=30,
    )
    if profile_response.status_code >= 400:
        return RedirectResponse(f"{settings.client_url}/import?github=error", status_code=302)
    profile = profile_response.json()
    try:
        user_id = ObjectId(payload["uid"])
    except InvalidId:
        return RedirectResponse(f"{settings.client_url}/?auth=github_error", status_code=302)
    user = database.db.users.find_one({"_id": user_id})
    if not user:
        return RedirectResponse(f"{settings.client_url}/?auth=github_error", status_code=302)
    database.db.users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "githubId": str(profile.get("id") or ""),
                "githubUsername": profile.get("login") or "",
                "githubAccessToken": encrypt(access_token),
                "updatedAt": datetime.now(timezone.utc),
            }
        },
    )
    return RedirectResponse(f"{settings.client_url}/import?github=connected", status_code=302)
