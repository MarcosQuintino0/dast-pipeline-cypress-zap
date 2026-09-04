"""
HAR file preprocessing.

This module is the heart of the data pipeline. It transforms
raw HAR files (with hundreds of duplicate requests, errors,
static assets) into a clean, optimized HAR ready for scanning.

PIPELINE:
1. Load all HARs from the traffic/ folder
2. Extract entries (each entry = 1 request + response)
3. Validate each entry's structure (Pydantic)
4. Filter: keep only 2xx status and allowed endpoints
5. Deduplicate: keep only 1 entry per METHOD|URL combination
6. Tokenize: replace numeric IDs with {{AUTO_INT}}
7. Save filtered HAR

WHY FILTER?
- Cypress generates traffic for CSS, JS, images, favicon, etc.
- We don't want ZAP wasting time scanning static assets
- Error responses (4xx, 5xx) can generate false positives

WHY DEDUPLICATE?
- The same endpoint can be called N times in tests
- Scanning the same endpoint 10x is a waste of time
- 1 call per METHOD|URL combination is sufficient

WHY TOKENIZE?
- ZAP sends hundreds of requests varying payloads
- If all use "userId: 1", it can cause conflicts
- Replacing with {{AUTO_INT}} allows generating unique values
"""

import glob
import json
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger
from pydantic import BaseModel, ValidationError

from security_tests.config import settings


class HTTPMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class MinimalRequest(BaseModel):
    """Minimum model a request must have in the HAR."""

    method: HTTPMethod
    url: str


class MinimalResponse(BaseModel):
    """Minimum model a response must have in the HAR."""

    status: int


class MinimalEntry(BaseModel):
    """A HAR entry is a request+response pair."""

    request: MinimalRequest
    response: MinimalResponse


def load_hars(folder: Path | None = None) -> list[dict[str, Any]]:
    """
    Loads all raw_traffic_*.har files from the folder.

    Returns a list with the JSON content of each HAR.
    Each HAR has the structure: {"log": {"entries": [...]}}
    """
    folder = folder or settings.TRAFFIC_DIR
    pattern = str(folder / "raw_traffic_*.har")
    files = glob.glob(pattern)

    if not files:
        logger.warning(f"No HAR files found in: {pattern}")
        return []

    hars: list[dict[str, Any]] = []
    for filepath in files:
        logger.info(f"Loading HAR: {filepath}")
        with open(filepath, encoding="utf-8") as f:
            hars.append(json.load(f))

    logger.info(f"Total HARs loaded: {len(hars)}")
    return hars


def extract_entries(hars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extracts all entries from a list of HARs."""
    entries: list[dict[str, Any]] = []
    for har in hars:
        try:
            new_entries = har["log"]["entries"]
            entries.extend(new_entries)
            logger.debug(f"Extracted {len(new_entries)} entries")
        except (KeyError, TypeError) as e:
            logger.warning(f"HAR with invalid structure: {e}")
    logger.info(f"Total entries extracted: {len(entries)}")
    return entries


def validate_entry(entry: dict[str, Any]) -> bool:
    """
    Validates that the entry has the minimum required structure.
    Uses Pydantic for typed validation.
    """
    try:
        MinimalEntry(**entry)
        return True
    except ValidationError:
        return False


def should_keep_entry(entry: dict[str, Any]) -> bool:
    """
    Applies business rules to decide if the entry should be kept.

    Rules:
    1. HTTP status must be 2xx (success)
    2. The endpoint must be in ENDPOINT_RULES
    3. The HTTP method must be allowed for that endpoint
    """
    status = entry["response"]["status"]
    if status < 200 or status >= 300:
        return False

    url = entry["request"]["url"]
    method = entry["request"]["method"]
    path = urlparse(url).path

    # Match the MOST SPECIFIC rule, not the first one declared.
    #
    # The rules use substring matching, so "/posts/1" matches both "/posts" and
    # "/posts/". Picking the first match in declaration order made the more
    # specific rule unreachable: "/posts" (GET, POST) always won, so PUT and
    # DELETE on "/posts/1" were dropped even though "/posts/" explicitly allows
    # them.
    #
    # The failure was invisible, which is what makes it serious. The pipeline
    # ran, the report came out clean, and the write operations — where injection
    # matters most — had simply never been scanned. Longest match wins, so the
    # narrower rule is the one that decides.
    matching = [
        (rule_path, allowed_methods)
        for rule_path, allowed_methods in settings.ENDPOINT_RULES.items()
        if rule_path in path
    ]

    if not matching:
        logger.debug(f"Endpoint not in rules: {path}")
        return False

    rule_path, allowed_methods = max(matching, key=lambda item: len(item[0]))

    if method not in allowed_methods:
        logger.debug(f"Method {method} not allowed for {path} (rule {rule_path})")
        return False

    return True


def generate_unique_key(entry: dict[str, Any]) -> str:
    """
    Generates deduplication key: METHOD|URL_WITHOUT_QUERY

    Example:
    - GET https://jsonplaceholder.typicode.com/posts?userId=1 → "GET|/posts"
    - GET https://jsonplaceholder.typicode.com/posts?userId=2 → "GET|/posts"
    → Both generate the same key, so only one will be kept.
    """
    url = entry["request"]["url"]
    method = entry["request"]["method"]
    path = urlparse(url).path
    return f"{method}|{path}"


def tokenize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Replaces numeric values of specific fields with {{AUTO_INT}}.

    Looks in the fields defined in FIELDS_TO_TOKENIZE.
    Only tokenizes if the value is numeric (int or numeric string).

    Example:
    {"userId": 1, "title": "foo"} → {"userId": "{{AUTO_INT}}", "title": "foo"}
    """
    request = entry.get("request", {})
    post_data = request.get("postData", {})
    text = post_data.get("text", "")

    if not text:
        return entry

    try:
        body = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return entry

    modified = False
    for field in settings.FIELDS_TO_TOKENIZE:
        if field in body:
            value = body[field]
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                body[field] = "{{AUTO_INT}}"
                modified = True

    if modified:
        entry["request"]["postData"]["text"] = json.dumps(body)
        logger.debug(f"Tokenized: {request.get('url', 'N/A')}")

    return entry


def rewrite_target_host(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Rewrites the target base URL to the address ZAP can actually reach.

    The HAR is recorded by the browser, so every URL points at
    http://localhost:3000. But the scan runs inside the ZAP container, and
    there "localhost" is ZAP itself, not the API. Without this rewrite ZAP
    would import the traffic, report zero reachable endpoints, and finish with
    an empty report that looks like a clean result.

    Rewriting here rather than in the Cypress layer keeps the browser traffic
    faithful to what a real client sees, and confines the container-networking
    detail to the one place that already reshapes the HAR.
    """
    de = settings.TARGET_URL
    para = settings.TARGET_URL_FROM_ZAP

    if de == para:
        return entry

    url = entry.get("request", {}).get("url", "")
    if url.startswith(de):
        entry["request"]["url"] = para + url[len(de) :]

    return entry


def filter_and_deduplicate_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Complete filtering and deduplication pipeline.

    1. Filters invalid entries (Pydantic validation)
    2. Filters by business rules (status, endpoint, method)
    3. Deduplicates by METHOD|URL key
    4. Tokenizes sensitive fields
    5. Rewrites the host to the address reachable from the ZAP container

    Returns a list of clean entries ready for ZAP.
    """
    seen: set[str] = set()
    result: list[dict[str, Any]] = []

    for entry in entries:
        # Step 1: Validate structure
        if not validate_entry(entry):
            continue

        # Step 2: Apply business rules
        if not should_keep_entry(entry):
            continue

        # Step 3: Deduplicate
        key = generate_unique_key(entry)
        if key in seen:
            logger.debug(f"Duplicate removed: {key}")
            continue
        seen.add(key)

        # Step 4: Tokenize
        entry = tokenize_entry(entry)

        # Step 5: Point the URL at the address ZAP reaches
        entry = rewrite_target_host(entry)

        result.append(entry)

    logger.info(f"Entries after filtering: {len(result)} (removed: {len(entries) - len(result)})")
    return result


def save_har(entries: list[dict[str, Any]], path: Path | None = None) -> Path:
    """
    Saves filtered entries into a new valid HAR file.

    The HAR format requires the structure:
    {"log": {"version": "1.2", "entries": [...]}}
    """
    path = path or (settings.TRAFFIC_DIR / "filtered_traffic.har")

    clean_har = {
        "log": {
            "version": "1.2",
            "creator": {"name": "dast-automation", "version": "1.0"},
            "entries": entries,
        }
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean_har, f, indent=2, ensure_ascii=False)

    logger.info(f"Filtered HAR saved to: {path}")
    return path
