import json
import re


def parse_model_json(text):
    trimmed = _unwrap_fence(str(text or "").strip())
    if not trimmed:
        raise ValueError("The model returned an empty document.")
    start = trimmed.find("{")
    if start < 0:
        raise ValueError("The model did not return a document.")
    candidate = _repair_json_escapes(trimmed[start:])
    for variant in (candidate, _close_truncated_json(candidate)):
        parsed = _loads_object(variant)
        if parsed is not None:
            return parsed
    raise ValueError("The model did not return a document.")


def _unwrap_fence(text):
    match = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if match:
        return match.group(1).strip()
    return text


def _repair_json_escapes(text):
    def replace(match):
        char = match.group(1)
        if char == "#":
            return char
        return "\\\\" + char

    return re.sub(r'\\([^"\\/bfnrtu])', replace, text)


def _close_truncated_json(text):
    in_string = False
    escape = False
    depth = 0
    started = False
    for char in text:
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
            started = True
        elif char == "}":
            depth = max(0, depth - 1)
    if not started:
        return text
    suffix = ""
    if escape:
        suffix += "\\"
    if in_string:
        suffix += '"'
    suffix += "}" * depth
    return text + suffix


def _loads_object(text):
    try:
        parsed, _end = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None
