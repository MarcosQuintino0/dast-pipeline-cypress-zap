"""
OWASP ZAP connection client.

ZAP exposes a local REST API that allows controlling
ALL features via code:
- Create sessions
- Import traffic
- Configure policies
- Run scans
- Generate reports

This module manages ZAP connection and verification.
"""

import time
from datetime import datetime

from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def create_zap_client() -> ZAPv2:
    """
    Creates and returns a ZAP client instance.

    ZAPv2 communicates with ZAP via HTTP (REST API).
    The proxy is the address where ZAP is listening.
    The apikey is required to authenticate the calls.
    """
    proxy = f"http://{settings.ZAP_HOST}:{settings.ZAP_PORT}"
    logger.info(f"Creating ZAP client at {proxy}")

    zap = ZAPv2(
        apikey=settings.ZAP_API_KEY,
        proxies={
            "http": proxy,
            "https": proxy,
        },
    )
    return zap


def test_connection(zap: ZAPv2, timeout: int = 30) -> None:
    """
    Tests if ZAP is online and responding.

    Polls every 2s until ZAP responds or timeout.
    This is necessary because ZAP can take time to start,
    especially in Docker containers.
    """
    logger.info(f"Testing ZAP connection (timeout: {timeout}s)...")
    start = time.time()

    while True:
        try:
            version = zap.core.version
            logger.info(f"ZAP connected! Version: {version}")
            return
        except Exception as e:
            elapsed = time.time() - start
            if elapsed > timeout:
                raise ConnectionError(
                    f"Could not connect to ZAP after {timeout}s. "
                    f"Check if ZAP is running at "
                    f"{settings.ZAP_HOST}:{settings.ZAP_PORT}"
                ) from e
            logger.debug(f"ZAP not available, retrying... ({elapsed:.0f}s)")
            time.sleep(2)


def create_clean_session(zap: ZAPv2) -> str:
    """
    Creates a new, clean session in ZAP.

    Each run should use an isolated session to avoid
    contamination from previous scan results.
    The name uses a timestamp for easy identification.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"scan_dast_{timestamp}"

    logger.info(f"Creating clean session: {session_name}")
    zap.core.new_session(name=session_name, overwrite=True)
    return session_name


def ensure_zap_mode(zap: ZAPv2) -> None:
    """
    Configures ZAP's operating mode.

    Modes:
    - safe: no attacks (observation only)
    - protect: attacks only URLs within scope
    - standard: default mode (recommended)
    - attack: aggressive mode
    """
    mode = settings.ZAP_MODE.value
    logger.info(f"Setting ZAP mode: {mode}")
    zap.core.set_mode(mode)
