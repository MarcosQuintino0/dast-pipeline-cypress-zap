"""
ZAP context and scope management.

The CONTEXT in ZAP defines:
1. Which URLs are "in scope" (will be scanned)
2. Which technologies to use in scan rules

WITHOUT context, ZAP may:
- Scan external URLs (dangerous!)
- Use rules for irrelevant technologies (slow)
- Generate unnecessary false positives

The technology allowlist drastically reduces scan time.
Example: if the API uses Node.js, there's no point testing
rules specific to PHP, ASP.NET, or MongoDB.
"""

from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def apply_technology_allowlist(zap: ZAPv2) -> str:
    """
    Creates context with scope and applies technology allowlist.

    Steps:
    1. Creates a new context in ZAP
    2. Defines scope regex (which URLs can be scanned)
    3. Excludes all technologies
    4. Includes only the technologies from the allowlist

    Returns the created context ID.
    """
    # Create context
    context_name = settings.ZAP_CONTEXT_NAME
    context_id = zap.context.new_context(context_name)
    logger.info(f"Context created: {context_name} (ID: {context_id})")

    # Define scope from the URL the ZAP container itself reaches. The scope is
    # what keeps the scan from wandering outside the target, so it has to match
    # the address ZAP actually sees, not the one the browser used.
    regex = f"{settings.TARGET_URL_FROM_ZAP}.*"
    zap.context.include_in_context(context_name, regex)
    logger.info(f"URL included in scope: {regex}")

    # Apply technology allowlist
    # First: exclude ALL
    zap.context.exclude_all_context_technologies(context_id)

    # Then: include only the relevant ones
    technologies = settings.ZAP_TECH_ALLOWLIST.split(",")
    for tech in technologies:
        tech = tech.strip()
        if tech:
            zap.context.include_context_technologies(context_id, tech)
            logger.debug(f"Technology included: {tech}")

    logger.info(f"Allowlist applied: {len(technologies)} technologies")
    return context_id
