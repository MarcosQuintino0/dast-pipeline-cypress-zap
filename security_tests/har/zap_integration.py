"""
Integration between HAR files and OWASP ZAP.

This module bridges the processed HAR and ZAP.
Responsibilities:
- Validate that the HAR exists
- Import the HAR into ZAP (it indexes all requests)
- Wait for passive scan to finish
- Extract unique targets (endpoints) for active scan
"""

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def validate_har_file(path: Path | None = None) -> Path:
    """
    Checks if the filtered HAR file exists.
    Raises FileNotFoundError if it doesn't.
    """
    path = path or (settings.TRAFFIC_DIR / "filtered_traffic.har")
    if not path.exists():
        raise FileNotFoundError(
            f"HAR not found: {path}. Run first: python -m security_tests.cli.process_har"
        )
    logger.info(f"HAR validated: {path}")
    return path


def path_inside_zap_container(path: Path) -> str:
    """
    Translates a host path into the path ZAP sees inside its container.

    The import API takes a file path and opens it on the filesystem of whoever
    runs ZAP. The HAR is written by Cypress on the host, and ZAP runs in a
    container, so the path has to be translated.

    Without the translation ZAP accepts the call, finds nothing, and every
    later scan is rejected with url_not_found — which surfaces as a report with
    zero alerts. A scan that never ran and a target with no findings look
    identical in the output, and only one of them is good news.

    The mount that makes both sides agree is declared in docker-compose.yml.
    """
    return f"{settings.ZAP_TRAFFIC_DIR_IN_CONTAINER}/{path.name}"


def import_har_into_zap(zap: ZAPv2, path: Path) -> None:
    """
    Imports the HAR file into ZAP via API.

    ZAP reads the HAR and indexes all requests internally. This populates the
    Site Tree and triggers the passive scan on each imported request. The Site
    Tree is also what the active scan checks against, so an endpoint missing
    here can never be attacked.
    """
    caminho_no_container = path_inside_zap_container(path)
    logger.info(f"Importing HAR into ZAP: {caminho_no_container} (host: {path})")

    result = zap.exim.import_har(caminho_no_container)
    logger.info(f"Import result: {result}")

    if isinstance(result, str) and result.strip().upper() not in {"OK", ""}:
        raise RuntimeError(
            f"ZAP could not import the HAR: {result!r}\n"
            f"Expected the file at {caminho_no_container} inside the container. "
            "Check the traffic volume in docker-compose.yml."
        )


def read_har(path: Path) -> dict[str, Any]:
    """Reads and returns the HAR JSON content."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def wait_for_passive_scan(zap: ZAPv2, timeout: int | None = None) -> None:
    """
    Waits for ZAP's passive scan queue to empty.

    The passive scan analyzes imported responses WITHOUT sending
    any additional traffic. It checks for:
    - Missing security headers
    - Cookies without Secure/HttpOnly flags
    - Exposed sensitive information
    - Etc.

    It's MANDATORY to wait for passive scan to finish before active,
    as active scan can interfere with passive results.
    """
    timeout = timeout or settings.ZAP_PSCAN_TIMEOUT_SECONDS
    logger.info(f"Waiting for passive scan (timeout: {timeout}s)...")

    start = time.time()
    while True:
        queue = int(zap.pscan.records_to_scan)
        elapsed = time.time() - start

        if queue == 0:
            logger.info(f"Passive scan completed in {elapsed:.0f}s")
            return

        if elapsed > timeout:
            logger.warning(
                f"Passive scan timeout ({timeout}s). {queue} records remaining in queue."
            )
            return

        logger.debug(f"Passive queue: {queue} records ({elapsed:.0f}s)")
        time.sleep(5)


def extract_targets_from_har(path: Path) -> list[tuple[str, str, str | None, str]]:
    """
    Extracts unique targets from HAR for active scan.

    Returns list of tuples:
    (full_url, method, body, path_without_query)

    The path_without_query is used for logging and deduplication.
    The body is included for POST/PUT requests.

    Example return:
    [
        ("https://jsonplaceholder.typicode.com/posts", "GET", None, "/posts"),
        ("https://jsonplaceholder.typicode.com/posts", "POST", '{"title":"foo"}', "/posts"),
    ]
    """
    har = read_har(path)
    entries = har.get("log", {}).get("entries", [])
    targets: list[tuple[str, str, str | None, str]] = []
    seen: set[str] = set()

    for entry in entries:
        req = entry.get("request", {})
        url = req.get("url", "")
        method = req.get("method", "GET")
        body = req.get("postData", {}).get("text", None)

        parsed = urlparse(url)
        clean_path = parsed.path

        key = f"{method}|{clean_path}"
        if key not in seen:
            seen.add(key)
            targets.append((url, method, body, clean_path))

    logger.info(f"Targets extracted for active scan: {len(targets)}")
    for _url, method, _, path in targets:
        logger.debug(f"  {method} {path}")

    return targets
