"""
ZAP HttpSender script management.

ZAP allows injecting JavaScript scripts that intercept
EVERY request before it's sent. We use this to:
- Replace {{AUTO_INT}} tokens with random values
- Ensure unique values on each scan request

The "httpsender" script type is executed automatically
for EVERY request ZAP makes (including active scan).
"""

from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def remove_script_if_exists(zap: ZAPv2, name: str) -> None:
    """
    Removes a script from ZAP if it already exists.

    Necessary to avoid duplicates when the pipeline
    is run multiple times in the same session.
    """
    try:
        scripts = zap.script.list_scripts
        for script in scripts:
            if script.get("name") == name:
                zap.script.remove(name)
                logger.info(f"Script removed: {name}")
                return
    except Exception:
        pass


def load_and_enable_script(zap: ZAPv2) -> None:
    """
    Loads the replace_tokens.js script into ZAP and enables it.

    The script is loaded as type "httpsender" with engine
    "Oracle Nashorn" (Java/ZAP JavaScript engine).

    Steps:
    1. Remove old script if it exists
    2. Load the .js file into ZAP
    3. Enable the script for automatic execution
    """
    script_name = "replace_tokens"
    path = settings.ZAP_SCRIPTS_DIR / "replace_tokens.js"

    if not path.exists():
        logger.warning(f"Script not found: {path}")
        return

    # Remove previous version
    remove_script_if_exists(zap, script_name)

    # Load script
    logger.info(f"Loading script: {path}")
    zap.script.load(
        scriptname=script_name,
        scripttype="httpsender",
        scriptengine="Oracle Nashorn",
        filename=str(path),
    )

    # Enable
    zap.script.enable(script_name)
    logger.info(f"Script '{script_name}' loaded and enabled")
