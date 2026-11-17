from app.errors import AppError
from app.lib.crypto import decrypt, encrypt
from app.lib.files import absolute_image_urls, folder_from_path, parse_repo, rewrite_images, select_files, title_from_path
from app.lib.folders import normalize_folder, slugify
from app.lib.model_json import parse_model_json


def test_parse_repo_accepts_a_url_and_a_short_name():
    assert parse_repo("https://github.com/facebook/react.git") == {"owner": "facebook", "repo": "react"}
    assert parse_repo("facebook/react") == {"owner": "facebook", "repo": "react"}
    try:
        parse_repo("https://gitlab.com/a/b")
    except AppError as error:
        assert "github.com" in str(error)
    else:
        raise AssertionError("expected a github.com error")


def test_folder_from_path_skips_generic_directories():
    assert folder_from_path("dsa/two-sum.js") == "dsa"
    assert folder_from_path("src/lib/sql/joins.sql") == "sql"
    assert folder_from_path("src/lib/app.js") is None
    assert folder_from_path("joins.sql") is None


def test_select_files_keeps_notes_first_and_caps_the_list():
    tree = [
        {"type": "blob", "path": "src/app.js", "size": 100},
        {"type": "blob", "path": "readme.md", "size": 100},
        {"type": "blob", "path": "node_modules/pkg/index.js", "size": 10},
        {"type": "blob", "path": "package-lock.json", "size": 10},
        {"type": "blob", "path": "photo.png", "size": 10},
        {"type": "blob", "path": "big.sql", "size": 90 * 1024},
    ]
    tree.extend({"type": "blob", "path": f"sql/file-{i}.sql", "size": 20} for i in range(30))
    selected = select_files(tree)
    assert len(selected["files"]) == 25
    assert selected["files"][0]["path"] == "readme.md"
    assert selected["skipped"]["byReason"]["ignored directory"] >= 1
    assert selected["skipped"]["byReason"]["over the 25 file limit"] >= 1
    assert selected["skipped"]["byReason"]["larger than 80 KB"] == 1
    assert all(item["path"] != "photo.png" for item in selected["skipped"]["samples"])


def test_rewrite_images_points_relative_figures_at_the_raw_repository():
    markdown = "See ![tree](./img/tree.png) and ![remote](https://example.com/a.png)"
    rewritten = rewrite_images(markdown, "ada", "notes", "main", "dsa/readme.md")
    assert "https://raw.githubusercontent.com/ada/notes/main/dsa/img/tree.png" in rewritten
    assert "https://example.com/a.png" in rewritten
    assert len(absolute_image_urls(rewritten)) == 2


def test_folder_names_and_model_json_are_normalized():
    assert slugify("SQL Queries") == "sql-queries"
    assert normalize_folder("data structures") == "DSA"
    assert normalize_folder("") == "General"
    parsed = parse_model_json('```json\n{"title":"Joins","folder":"SQL","markdown":"# Joins"}\n```')
    assert parsed["title"] == "Joins"
    note = (
        '{"title":"Binary Search","folder":"DSA","markdown":"# Binary Search\\n'
        '```mermaid\\ngraph TD\\n    B{Find Midpoint}\\n```\\n\\### Walkthrough"}'
    )
    parsed = parse_model_json(note)
    assert parsed["folder"] == "DSA"
    assert "{Find Midpoint}" in parsed["markdown"]
    assert "### Walkthrough" in parsed["markdown"]
    truncated = parse_model_json('{"title":"Binary Search","folder":"DSA","markdown":"# Binary')
    assert truncated["title"] == "Binary Search"
    assert truncated["markdown"].startswith("# Binary")
    assert title_from_path("src/two_sum.js") == "Two sum"


def test_github_tokens_round_trip():
    secret = encrypt("gho_example")
    assert secret != "gho_example"
    assert decrypt(secret) == "gho_example"
