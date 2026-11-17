import posixpath
import re
from urllib.parse import quote

from app.errors import AppError

EXTENSIONS = {
    "md", "txt", "js", "jsx", "ts", "tsx", "py", "java", "c", "cpp", "go", "rs", "sql", "json", "yml", "yaml",
}
GENERIC_DIRS = {
    "src", "lib", "docs", "source", "app", "packages", "pkg", "internal", "main", "test", "tests", "__tests__",
}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "coverage", "vendor", ".next", "out", "__pycache__", ".venv", "venv",
}
LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "composer.lock",
    "gemfile.lock", "poetry.lock", "cargo.lock",
}
FILE_CAP = 25
MAX_FILE_BYTES = 80 * 1024

URL_RE = re.compile(r"^https?://([^/]+)/([^/\s]+)/([^/\s#?]+)", re.I)
SHORT_RE = re.compile(r"^([^/\s]+)/([^/\s]+)$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)")
IMG_TAG_RE = re.compile(r"(<img\b[^>]*\bsrc=[\"'])([^\"']+)([\"'][^>]*>)", re.I)
ABS_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")


def parse_repo(value):
    trimmed = str(value or "").strip()
    if trimmed.endswith(".git"):
        trimmed = trimmed[:-4]
    if not trimmed:
        raise AppError("Enter a GitHub repository.", 400)
    url_match = URL_RE.match(trimmed)
    if url_match:
        if not re.match(r"^(www\.)?github\.com$", url_match.group(1), re.I):
            raise AppError("Only github.com repositories are supported.", 400)
        return {"owner": url_match.group(2), "repo": url_match.group(3)}
    short_match = SHORT_RE.match(trimmed)
    if short_match and ":" not in short_match.group(1):
        return {"owner": short_match.group(1), "repo": short_match.group(2)}
    raise AppError("Use owner/repo or a https://github.com/owner/repo URL.", 400)


def folder_from_path(file_path):
    parts = [part for part in str(file_path or "").split("/")[:-1] if part]
    for part in parts:
        if part.lower() not in GENERIC_DIRS:
            return part
    return None


def _extension_of(file_path):
    base = file_path.split("/")[-1]
    dot = base.rfind(".")
    if dot <= 0:
        return ""
    return base[dot + 1 :].lower()


def _in_skipped_dir(file_path):
    return any(part in SKIP_DIRS or (part.startswith(".") and part != ".") for part in file_path.split("/"))


def select_files(tree):
    by_reason = {}
    samples = []
    candidates = []

    def bump(reason, file_path, keep_sample):
        by_reason[reason] = by_reason.get(reason, 0) + 1
        if keep_sample and len(samples) < 12:
            samples.append({"path": file_path, "reason": reason})

    for item in tree or []:
        if not item or item.get("type") != "blob" or not item.get("path"):
            continue
        file_path = item["path"]
        base = file_path.split("/")[-1]
        if _in_skipped_dir(file_path):
            bump("ignored directory", file_path, False)
            continue
        if base.lower() in LOCKFILES or base.endswith(".min.js"):
            bump("lockfile or generated file", file_path, True)
            continue
        if _extension_of(file_path) not in EXTENSIONS:
            bump("unsupported file", file_path, False)
            continue
        if (item.get("size") or 0) > MAX_FILE_BYTES:
            bump("larger than 80 KB", file_path, True)
            continue
        candidates.append(item)

    def sort_key(item):
        doc = 0 if re.search(r"\.(md|txt)$", item["path"], re.I) else 1
        return (doc, item["path"])

    candidates.sort(key=sort_key)
    files = candidates[:FILE_CAP]
    for item in candidates[FILE_CAP:]:
        bump("over the 25 file limit", item["path"], True)
    total = sum(by_reason.values())
    return {"files": files, "skipped": {"total": total, "byReason": by_reason, "samples": samples}}


def rewrite_images(markdown, owner, repo, branch, file_path):
    directory = posixpath.dirname(file_path)
    base_dir = "" if directory == "." else directory

    def to_raw(src):
        if re.match(r"^(https?:|data:|//)", src, re.I) or src.startswith("#"):
            return None
        joined = posixpath.normpath(posixpath.join(base_dir, src))
        if not joined or joined.startswith(".."):
            return None
        encoded = "/".join(quote(part, safe="") for part in joined.split("/"))
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{quote(branch, safe='')}/{encoded}"

    def replace_markdown(match):
        url = to_raw(match.group(2))
        if not url:
            return match.group(0)
        return f"![{match.group(1)}]({url})"

    def replace_tag(match):
        url = to_raw(match.group(2))
        if not url:
            return match.group(0)
        return f"{match.group(1)}{url}{match.group(3)}"

    rewritten = IMAGE_RE.sub(replace_markdown, str(markdown or ""))
    return IMG_TAG_RE.sub(replace_tag, rewritten)


def absolute_image_urls(markdown):
    return ABS_IMAGE_RE.findall(str(markdown or ""))


def title_from_path(file_path):
    base = (str(file_path).split("/")[-1] or "note")
    base = re.sub(r"\.[^.]+$", "", base)
    words = re.sub(r"[_-]+", " ", base).strip()
    if not words:
        return "Note"
    return words[0].upper() + words[1:]
