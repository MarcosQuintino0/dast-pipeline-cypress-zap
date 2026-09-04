"""
Active scan execution, endpoint by endpoint.

WHY SCAN ONE ENDPOINT AT A TIME?
- Fine-grained progress control (know which endpoint is being scanned)
- Ability to skip problematic endpoints
- Detailed per-endpoint logging
- Ability to run actions between endpoints (e.g., cleanup)

The active scan sends malicious payloads (SQL injection, XSS, etc.)
and analyzes responses to detect vulnerabilities.
"""

import time
from typing import Any
from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def get_context_id(zap: ZAPv2, name: str = "DAST_JSONPlaceholder") -> str | None:
    """
    Looks up the context ID by name.

    The ID is needed to associate the scan with the correct context,
    ensuring only URLs in scope are attacked.
    """
    contexts = zap.context.context(name)
    context_id = contexts.get("id", None)
    if context_id:
        logger.debug(f"Context '{name}' found: ID {context_id}")
    else:
        logger.warning(f"Context '{name}' not found!")
    return context_id


def build_scan_kwargs(
    url: str, method: str, body: str | None = None, context_id: str | None = None
) -> dict[str, Any]:
    """
    Builds the parameters for the ZAP scan call.

    kwargs are passed directly to zap.ascan.scan().
    """
    kwargs = {
        "url": url,
        "method": method,
        "scanpolicyname": "Default Policy",
    }

    if context_id:
        kwargs["contextid"] = context_id

    if body and method in ("POST", "PUT", "PATCH"):
        kwargs["postdata"] = body

    return kwargs


def monitor_scan_progress(
    zap: ZAPv2, scan_id: str, url_display: str
) -> None:
    """
    Monitors active scan progress until 100%.

    Logs every 10% to avoid cluttering the output.
    The scan can take from seconds to minutes depending on the endpoint
    and the attack strength configuration.
    """
    last_logged = -1

    while True:
        progress = int(zap.ascan.status(scan_id))

        if progress >= 100:
            logger.info(f"  Scan complete: {url_display}")
            break

        # Log every 10%
        tenth = progress // 10
        if tenth > last_logged:
            last_logged = tenth
            logger.info(f"  Progress: {progress}% - {url_display}")

        time.sleep(3)


def run_scan_on_endpoint(
    zap: ZAPv2,
    url: str,
    method: str,
    body: str | None = None,
    url_display: str = "",
    context_id: str | None = None,
) -> None:
    """
    Runs active scan on a single endpoint.

    Steps:
    1. Build scan parameters
    2. Start scan via API
    3. Monitor progress until completion

    If the scan fails to start, logs the error and moves on
    to the next endpoint (does not interrupt the pipeline).
    """
    logger.info(f"Starting scan: {method} {url_display}")

    kwargs = build_scan_kwargs(url, method, body, context_id)

    try:
        scan_id = zap.ascan.scan(**kwargs)

        if scan_id is None or str(scan_id).startswith("url_not"):
            logger.warning(
                f"  ZAP rejected scan on {url_display}: {scan_id}"
            )
            return

        logger.info(f"  Scan ID: {scan_id}")
        monitor_scan_progress(zap, scan_id, url_display)

    except Exception as e:
        logger.error(f"  Scan error on {url_display}: {e}")
