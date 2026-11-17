from typing import Optional

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import ReturnDocument

from app import db as database
from app.deps import require_user
from app.lib.folders import slugify

router = APIRouter()


class FolderIn(BaseModel):
    name: str = ""


class NoteIn(BaseModel):
    title: Optional[str] = None
    markdown: Optional[str] = None
    folderId: Optional[str] = None


def _object_id(value, message):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=message)


@router.get("/api/folders")
def list_folders(user=Depends(require_user)):
    folders = list(database.db.folders.find({"userId": user["_id"]}).sort("name", 1))
    notes = list(database.db.notes.find({"userId": user["_id"]}, {"title": 1, "folderId": 1}).sort("title", 1))
    by_folder = {}
    for note in notes:
        by_folder.setdefault(note["folderId"], []).append({"id": str(note["_id"]), "title": note.get("title") or "Untitled"})
    return {
        "folders": [
            {
                "id": str(folder["_id"]),
                "name": folder.get("name") or "Folder",
                "slug": folder.get("slug") or "",
                "notes": by_folder.get(folder["_id"], []),
            }
            for folder in folders
        ]
    }


@router.patch("/api/folders/{folder_id}")
def rename_folder(folder_id: str, body: FolderIn, user=Depends(require_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name is required.")
    slug = slugify(name)
    oid = _object_id(folder_id, "Folder not found.")
    conflict = database.db.folders.find_one({"userId": user["_id"], "slug": slug, "_id": {"$ne": oid}})
    if conflict:
        raise HTTPException(status_code=409, detail="A folder with that name already exists.")
    folder = database.db.folders.find_one_and_update(
        {"_id": oid, "userId": user["_id"]},
        {"$set": {"name": name[:48], "slug": slug, "updatedAt": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")
    return {"folder": {"id": str(folder["_id"]), "name": folder["name"], "slug": folder["slug"]}}


@router.delete("/api/folders/{folder_id}")
def delete_folder(folder_id: str, user=Depends(require_user)):
    oid = _object_id(folder_id, "Folder not found.")
    folder = database.db.folders.find_one_and_delete({"_id": oid, "userId": user["_id"]})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")
    database.db.notes.delete_many({"userId": user["_id"], "folderId": folder["_id"]})
    return {"ok": True}


def _present_note(note, folder):
    updated = note.get("updatedAt")
    return {
        "id": str(note["_id"]),
        "title": note.get("title") or "Untitled",
        "markdown": note.get("markdown") or "",
        "source": note.get("source") or "",
        "repo": note.get("repo") or "",
        "path": note.get("path") or "",
        "folderId": str(note.get("folderId") or ""),
        "folderName": folder.get("name") if folder else "",
        "folderSlug": folder.get("slug") if folder else "",
        "updatedAt": updated.isoformat() if updated else "",
    }


@router.get("/api/notes/{note_id}")
def get_note(note_id: str, user=Depends(require_user)):
    note = database.db.notes.find_one({"_id": _object_id(note_id, "Note not found."), "userId": user["_id"]})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    folder = database.db.folders.find_one({"_id": note.get("folderId"), "userId": user["_id"]})
    return {"note": _present_note(note, folder)}


@router.patch("/api/notes/{note_id}")
def update_note(note_id: str, body: NoteIn, user=Depends(require_user)):
    note = database.db.notes.find_one({"_id": _object_id(note_id, "Note not found."), "userId": user["_id"]})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    updates = {"updatedAt": datetime.now(timezone.utc)}
    if isinstance(body.title, str) and body.title.strip():
        updates["title"] = body.title.strip()[:120]
    if isinstance(body.markdown, str):
        updates["markdown"] = body.markdown
    if body.folderId:
        folder = database.db.folders.find_one({"_id": _object_id(body.folderId, "Folder not found."), "userId": user["_id"]})
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found.")
        updates["folderId"] = folder["_id"]
    database.db.notes.update_one({"_id": note["_id"]}, {"$set": updates})
    return {"note": {"id": str(note["_id"]), "title": updates.get("title", note.get("title")), "folderId": str(updates.get("folderId", note.get("folderId")))}}


@router.delete("/api/notes/{note_id}")
def delete_note(note_id: str, user=Depends(require_user)):
    note = database.db.notes.find_one_and_delete({"_id": _object_id(note_id, "Note not found."), "userId": user["_id"]})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    return {"ok": True}
