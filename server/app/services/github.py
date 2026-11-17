from urllib.parse import quote

import httpx

from app.config import settings
from app.errors import AppError


def _headers(token, accept="application/vnd.github+json"):
    headers = {
        "Accept": accept,
        "User-Agent": "notes-ai",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    bearer = token or settings.github_token
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    return headers


def github_fetch(path, token="", accept="application/vnd.github+json"):
    return httpx.get(
        f"https://api.github.com{path}",
        headers=_headers(token, accept),
        timeout=40,
        follow_redirects=True,
    )


def _rate_limit():
    raise AppError("GitHub rate limit reached. Connect GitHub or set GITHUB_TOKEN on the server.", 429)


def fetch_repo_bundle(owner, repo, token=""):
    meta_response = github_fetch(f"/repos/{owner}/{repo}", token)
    if meta_response.status_code == 404:
        raise AppError("Repository not found. If it is private, connect GitHub and try again.", 404)
    if meta_response.status_code in (403, 429):
        _rate_limit()
    if meta_response.status_code >= 400:
        raise AppError(f"GitHub could not read this repository ({meta_response.status_code}).", 502)
    meta = meta_response.json()
    branch = meta.get("default_branch") or "HEAD"
    tree_response = github_fetch(
        f"/repos/{owner}/{repo}/git/trees/{quote(branch, safe='')}?recursive=1",
        token,
    )
    if tree_response.status_code in (403, 429):
        _rate_limit()
    if tree_response.status_code >= 400:
        raise AppError("GitHub could not list the files in this repository.", 502)
    tree = tree_response.json()
    return {
        "fullName": meta.get("full_name") or f"{owner}/{repo}",
        "branch": branch,
        "private": bool(meta.get("private")),
        "truncated": bool(tree.get("truncated")),
        "tree": tree.get("tree") or [],
    }


def fetch_file_text(owner, repo, branch, file_path, token=""):
    encoded = "/".join(quote(part, safe="") for part in file_path.split("/"))
    response = github_fetch(
        f"/repos/{owner}/{repo}/contents/{encoded}?ref={quote(branch, safe='')}",
        token,
        "application/vnd.github.raw",
    )
    if response.status_code in (403, 429):
        _rate_limit()
    if response.status_code >= 400:
        raise AppError(f"Could not read {file_path}.", 502)
    return response.text


def list_user_repos(token):
    response = github_fetch(
        "/user/repos?per_page=50&sort=updated&affiliation=owner,collaborator,organization_member",
        token,
    )
    if response.status_code == 401:
        raise AppError("GitHub access expired. Connect GitHub again.", 401)
    if response.status_code >= 400:
        raise AppError("Could not list GitHub repositories.", 502)
    return [
        {
            "fullName": repo.get("full_name") or "",
            "private": bool(repo.get("private")),
            "description": repo.get("description") or "",
            "language": repo.get("language") or "",
        }
        for repo in response.json()
    ]
