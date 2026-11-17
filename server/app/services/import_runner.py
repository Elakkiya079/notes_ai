import queue
import threading
import uuid

from app import db as database
from app.lib.crypto import decrypt
from app.lib.files import absolute_image_urls, folder_from_path, rewrite_images, select_files, title_from_path
from app.services.gemini import document_from_file, document_from_topic
from app.services.github import fetch_file_text, fetch_repo_bundle


def _mark_failed(job_id, error):
    database.db.import_jobs.update_one(
        {"_id": job_id},
        {"$set": {"status": "failed", "error": str(error) or "Import failed."}},
    )


def _guard(fn, job_id, token):
    try:
        fn(job_id, token)
    except Exception as error:
        _mark_failed(job_id, error)


def start_repo_import(job_id, user):
    token = ""
    if user.get("githubAccessToken"):
        try:
            token = decrypt(user["githubAccessToken"])
        except Exception:
            token = ""
    threading.Thread(target=_guard, args=(run_repo_import, job_id, token), daemon=True).start()


def start_topic_import(job_id):
    threading.Thread(target=_guard, args=(run_topic_import, job_id, ""), daemon=True).start()


def run_topic_import(job_id, _token=""):
    job = database.db.import_jobs.find_one({"_id": job_id})
    if not job:
        return
    database.db.import_jobs.update_one(
        {"_id": job_id},
        {"$set": {"status": "generating", "progress": {"done": 0, "total": 1}}},
    )
    drafted = document_from_topic(job["input"])
    database.db.import_jobs.update_one(
        {"_id": job_id},
        {
            "$push": {
                "documents": {
                    "id": uuid.uuid4().hex,
                    "title": drafted["title"],
                    "folderName": drafted["folderName"],
                    "markdown": drafted["markdown"],
                    "sourcePath": job["input"],
                    "included": True,
                    "error": "",
                }
            },
            "$set": {"status": "review", "progress": {"done": 1, "total": 1}},
        },
    )


def run_repo_import(job_id, token):
    job = database.db.import_jobs.find_one({"_id": job_id})
    if not job:
        return
    owner, repo = job["input"].split("/", 1)
    bundle = fetch_repo_bundle(owner, repo, token)
    selected = select_files(bundle["tree"])
    if bundle["truncated"]:
        reason = "repository listing was truncated"
        selected["skipped"]["byReason"][reason] = selected["skipped"]["byReason"].get(reason, 0) + 1
        selected["skipped"]["total"] += 1

    database.db.import_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "repoFullName": bundle["fullName"],
                "branch": bundle["branch"],
                "skipped": selected["skipped"],
                "status": "generating",
                "progress": {"done": 0, "total": len(selected["files"])},
            }
        },
    )
    if not selected["files"]:
        _mark_failed(
            job_id,
            "No supported text files were found. Try a repository with source files or notes, or enter a topic instead.",
        )
        return

    work = queue.Queue()
    for item in selected["files"]:
        work.put(item)

    def worker():
        while True:
            try:
                item = work.get_nowait()
            except queue.Empty:
                return
            _draft_file(job_id, item, owner, repo, bundle["branch"], token)

    threads = [threading.Thread(target=worker) for _ in range(min(2, len(selected["files"])))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    database.db.import_jobs.update_one(
        {"_id": job_id, "status": {"$ne": "failed"}},
        {"$set": {"status": "review"}},
    )


def _draft_file(job_id, file, owner, repo, branch, token):
    source_path = file["path"]
    folder_hint = folder_from_path(source_path)
    fallback_title = title_from_path(source_path)
    try:
        content = fetch_file_text(owner, repo, branch, source_path, token)
        if not content.strip():
            raise ValueError("The file is empty.")
        content = rewrite_images(content, owner, repo, branch, source_path)
        drafted = document_from_file(source_path, content, folder_hint, owner, repo, fallback_title)
        markdown = drafted["markdown"]
        missing = [url for url in absolute_image_urls(content) if url not in markdown]
        if missing:
            markdown += "\n\n## Figures\n\n" + "\n\n".join(f"![Figure]({url})" for url in missing)
        document = {
            "id": uuid.uuid4().hex,
            "title": drafted["title"],
            "folderName": folder_hint or drafted["folderName"],
            "markdown": markdown,
            "sourcePath": source_path,
            "included": True,
            "error": "",
        }
    except Exception as error:
        document = {
            "id": uuid.uuid4().hex,
            "title": fallback_title,
            "folderName": folder_hint or "General",
            "markdown": "",
            "sourcePath": source_path,
            "included": False,
            "error": str(error) or "Could not draft this file.",
        }
    database.db.import_jobs.update_one(
        {"_id": job_id},
        {"$push": {"documents": document}, "$inc": {"progress.done": 1}},
    )
