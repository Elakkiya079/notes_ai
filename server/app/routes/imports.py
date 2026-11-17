from typing import Optional

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db as database
from app.config import settings
from app.deps import require_user
from app.errors import AppError
from app.lib.files import parse_repo
from app.lib.folders import clean_title, normalize_folder, slugify
from app.services.import_runner import start_repo_import, start_topic_import

router = APIRouter()


class RepoIn(BaseModel):
    url: Optional[str] = None
    repo: Optional[str] = None


class TopicIn(BaseModel):
    topic: str = ""


class SaveDoc(BaseModel):
    id: str
    title: Optional[str] = None
    folderName: Optional[str] = None
    included: bool = True


class SaveIn(BaseModel):
    documents: list[SaveDoc] = []


def _object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Import not found.")


def present_job(job):
    skipped = job.get("skipped") or {}
    by_reason = skipped.get("byReason") or {}
    if not isinstance(by_reason, dict):
        by_reason = dict(by_reason)
    return {
        "id": str(job["_id"]),
        "kind": job.get("kind"),
        "input": job.get("input"),
        "status": job.get("status"),
        "error": job.get("error") or "",
        "progress": job.get("progress") or {"done": 0, "total": 0},
        "skipped": {
            "total": skipped.get("total") or 0,
            "byReason": by_reason,
            "samples": skipped.get("samples") or [],
        },
        "repoFullName": job.get("repoFullName") or "",
        "branch": job.get("branch") or "",
        "documents": [
            {
                "id": doc.get("id"),
                "title": doc.get("title") or "",
                "folderName": doc.get("folderName") or "General",
                "markdown": doc.get("markdown") or "",
                "sourcePath": doc.get("sourcePath") or "",
                "included": bool(doc.get("included")),
                "error": doc.get("error") or "",
            }
            for doc in job.get("documents") or []
        ],
    }


@router.post("/api/import/repo", status_code=202)
def import_repo(body: RepoIn, user=Depends(require_user)):
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not set on the server.")
    try:
        parsed = parse_repo(body.url or body.repo or "")
    except AppError as error:
        raise HTTPException(status_code=error.status, detail=str(error)) from error
    now = datetime.now(timezone.utc)
    inserted = database.db.import_jobs.insert_one(
        {
            "userId": user["_id"],
            "kind": "repo",
            "input": f"{parsed['owner']}/{parsed['repo']}",
            "status": "fetching",
            "error": "",
            "progress": {"done": 0, "total": 0},
            "skipped": {"total": 0, "byReason": {}, "samples": []},
            "repoFullName": "",
            "branch": "",
            "documents": [],
            "createdAt": now,
            "updatedAt": now,
        }
    )
    job = database.db.import_jobs.find_one({"_id": inserted.inserted_id})
    start_repo_import(job["_id"], user)
    return {"job": present_job(job)}


@router.post("/api/import/topic", status_code=202)
def import_topic(body: TopicIn, user=Depends(require_user)):
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not set on the server.")
    topic = body.topic.strip()
    if len(topic) < 2:
        raise HTTPException(status_code=400, detail="Enter a topic to write about.")
    now = datetime.now(timezone.utc)
    inserted = database.db.import_jobs.insert_one(
        {
            "userId": user["_id"],
            "kind": "topic",
            "input": topic[:200],
            "status": "generating",
            "error": "",
            "progress": {"done": 0, "total": 1},
            "skipped": {"total": 0, "byReason": {}, "samples": []},
            "repoFullName": "",
            "branch": "",
            "documents": [],
            "createdAt": now,
            "updatedAt": now,
        }
    )
    job = database.db.import_jobs.find_one({"_id": inserted.inserted_id})
    start_topic_import(job["_id"])
    return {"job": present_job(job)}


@router.get("/api/import/{job_id}")
def get_import(job_id: str, user=Depends(require_user)):
    job = database.db.import_jobs.find_one({"_id": _object_id(job_id), "userId": user["_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Import not found.")
    return {"job": present_job(job)}


@router.post("/api/import/{job_id}/save")
def save_import(job_id: str, body: SaveIn, user=Depends(require_user)):
    job = database.db.import_jobs.find_one({"_id": _object_id(job_id), "userId": user["_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Import not found.")
    if job.get("status") != "review":
        raise HTTPException(status_code=409, detail="This import is not ready to save.")

    edits = {item.id: item for item in body.documents}
    chosen = []
    for doc in job.get("documents") or []:
        edit = edits.get(doc.get("id"))
        included = edit.included if edit else bool(doc.get("included"))
        if not included or doc.get("error") or not doc.get("markdown"):
            continue
        folder_name = normalize_folder(edit.folderName if edit and edit.folderName else doc.get("folderName"))
        chosen.append(
            {
                "title": clean_title(edit.title if edit else None, doc.get("title")),
                "folderName": folder_name,
                "markdown": doc.get("markdown") or "",
                "sourcePath": doc.get("sourcePath") or "",
            }
        )
    if not chosen:
        raise HTTPException(status_code=400, detail="Choose at least one document to add.")

    saved = []
    now = datetime.now(timezone.utc)
    for doc in chosen:
        slug = slugify(doc["folderName"])
        folder = database.db.folders.find_one({"userId": user["_id"], "slug": slug})
        if not folder:
            inserted = database.db.folders.insert_one(
                {"userId": user["_id"], "name": doc["folderName"], "slug": slug, "createdAt": now, "updatedAt": now}
            )
            folder = database.db.folders.find_one({"_id": inserted.inserted_id})
        note = {
            "userId": user["_id"],
            "folderId": folder["_id"],
            "title": doc["title"],
            "markdown": doc["markdown"],
            "source": "topic" if job.get("kind") == "topic" else "github-file",
            "repo": job.get("repoFullName") or "",
            "path": doc["sourcePath"],
            "createdAt": now,
            "updatedAt": now,
        }
        inserted = database.db.notes.insert_one(note)
        saved.append(
            {
                "id": str(inserted.inserted_id),
                "title": doc["title"],
                "folderSlug": folder["slug"],
                "folderName": folder["name"],
            }
        )
    database.db.import_jobs.update_one({"_id": job["_id"]}, {"$set": {"status": "saved", "updatedAt": now}})
    return {"notes": saved}
