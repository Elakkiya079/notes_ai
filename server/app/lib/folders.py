import re

FOLDER_ALIASES = [
    (re.compile(r"^(dsa|data structures?( and algorithms)?|algorithms?|leetcode)$", re.I), "DSA"),
    (re.compile(r"^(sql|databases?|postgres|postgresql|mysql)$", re.I), "SQL"),
    (re.compile(r"^(react|reactjs|react\.js)$", re.I), "React"),
    (re.compile(r"^(javascript|js|node|node\.js|nodejs)$", re.I), "JavaScript"),
    (re.compile(r"^(typescript|ts)$", re.I), "TypeScript"),
    (re.compile(r"^(python|py)$", re.I), "Python"),
    (re.compile(r"^(java)$", re.I), "Java"),
    (re.compile(r"^(golang|go)$", re.I), "Go"),
    (re.compile(r"^(rust)$", re.I), "Rust"),
    (re.compile(r"^(system design)$", re.I), "System Design"),
    (re.compile(r"^(operating systems?|os)$", re.I), "Operating Systems"),
    (re.compile(r"^(css)$", re.I), "CSS"),
    (re.compile(r"^(html)$", re.I), "HTML"),
]


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower().strip().replace("'", "").replace('"', ""))
    slug = slug.strip("-")
    return slug or "general"


def normalize_folder(name):
    trimmed = re.sub(r"\s+", " ", str(name or "").strip().strip("\"'")).strip()
    if not trimmed:
        return "General"
    for pattern, label in FOLDER_ALIASES:
        if pattern.match(trimmed):
            return label
    return trimmed[:48]


def clean_title(name, fallback):
    trimmed = re.sub(r"\s+", " ", str(name or "").strip().strip("\"'")).strip()
    return (trimmed or fallback or "Untitled")[:120]
