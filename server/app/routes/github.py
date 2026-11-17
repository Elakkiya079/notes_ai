from fastapi import APIRouter, Depends, HTTPException

from app.deps import require_user
from app.errors import AppError
from app.lib.crypto import decrypt
from app.services.github import list_user_repos

router = APIRouter()


@router.get("/api/github/repos")
def repos(user=Depends(require_user)):
    if not user.get("githubAccessToken"):
        return {"connected": False, "repos": []}
    try:
        token = decrypt(user["githubAccessToken"])
    except Exception:
        raise HTTPException(status_code=401, detail="GitHub access could not be read. Connect GitHub again.")
    try:
        listed = list_user_repos(token)
    except AppError as error:
        raise HTTPException(status_code=error.status, detail=str(error)) from error
    return {"connected": True, "repos": listed}
