import time

import google.generativeai as genai

from app.config import settings
from app.errors import AppError
from app.lib.files import absolute_image_urls
from app.lib.folders import clean_title, normalize_folder
from app.lib.model_json import parse_model_json


def _model():
    if not settings.gemini_api_key:
        raise AppError("GEMINI_API_KEY is not set on the server.", 503)
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        settings.gemini_model,
        generation_config={
            "response_mime_type": "application/json",
            "max_output_tokens": 8192,
        },
    )


def _generate(prompt):
    generative_model = _model()

    def once():
        try:
            result = generative_model.generate_content(prompt)
            return result.text
        except Exception as error:
            message = str(error) or "Gemini could not write this document."
            raise AppError(message, 502) from error

    def once_with_retry():
        try:
            return once()
        except AppError as error:
            if "429" in str(error) or "quota" in str(error).lower() or "resource exhausted" in str(error).lower():
                time.sleep(5)
                return once()
            raise

    last_error = None
    for _attempt in range(2):
        text = once_with_retry()
        try:
            parse_model_json(text)
            return text
        except (ValueError, TypeError) as error:
            last_error = error
    raise AppError(str(last_error), 502)


def _document_from_model(text, folder_hint, fallback_title, source):
    try:
        parsed = parse_model_json(text)
    except (ValueError, TypeError) as error:
        raise AppError(str(error), 502) from error
    folder_name = folder_hint or normalize_folder(parsed.get("folder"))
    markdown = str(parsed.get("markdown") or "").strip()
    missing = [url for url in absolute_image_urls(source) if url not in markdown]
    if missing:
        figures = "\n\n".join(f"![Figure]({url})" for url in missing)
        markdown = f"{markdown}\n\n## Figures\n\n{figures}".strip()
    if not markdown:
        raise AppError("The model returned an empty document.", 502)
    return {
        "title": clean_title(parsed.get("title"), fallback_title),
        "folderName": folder_name,
        "markdown": markdown,
    }


def document_from_file(file_path, content, folder_hint, owner, repo, fallback_title):
    is_markdown = file_path.lower().endswith((".md", ".txt"))
    clipped = content[:24000] + ("\n\n[truncated]" if len(content) > 24000 else "")
    if folder_hint:
        folder_rule = f"folder MUST be exactly {folder_hint!r}."
    else:
        folder_rule = (
            "folder is a short subject name a student would recognize, such as DSA, SQL, React, or Python. "
            "Decide it only from this file. Do not use src, lib, or docs."
        )
    prose_rule = (
        "- This file is already prose. Keep its facts, headings, and images. Repair structure so it is easy to read. "
        "Do not invent sections that are not supported by the file."
        if is_markdown
        else "- Explain the file so it can be studied later. Start with a short summary of what the file does. "
        "Keep the important code in fenced blocks with a language tag. Do not paste the whole file when it is long."
    )
    prompt = f"""You turn a repository file into a study note.

Return JSON with keys title, folder, and markdown.
- title is a short human name, not a file path.
- {folder_rule}
- markdown is GitHub-flavored markdown.
{prose_rule}
- Add a markdown table when a comparison, complexity list, or field list is actually in the source.
- Add one mermaid diagram inside a mermaid fence when the source has a flow, call order, or structure worth drawing. Skip the diagram when it would only decorate the page.
- Do not invent behavior that is not in the source.
- Keep any http image URLs that are already in the source.
- No text outside the JSON.

Repository: {owner}/{repo}
File: {file_path}

SOURCE:
{clipped}"""
    text = _generate(prompt)
    return _document_from_model(text, folder_hint, fallback_title, content)


def document_from_topic(topic):
    prompt = f"""You write a study note on a topic.

Return JSON with keys title, folder, and markdown.
- title is the topic in a short readable form.
- folder is the subject a student would file this under, such as DSA, SQL, React, or Operating Systems.
- markdown is GitHub-flavored markdown for someone learning the topic.
- Open with a short explanation in plain language.
- Use sections, a worked example, and fenced code when code helps.
- Include one markdown table when a comparison or complexity summary helps.
- Include one mermaid diagram inside a mermaid fence when a process or structure is easier to see than to read. Skip it when it does not help.
- Be accurate. Prefer a smaller correct note over a long speculative one.
- No text outside the JSON.

Topic: {topic}"""
    text = _generate(prompt)
    return _document_from_model(text, None, topic, "")
