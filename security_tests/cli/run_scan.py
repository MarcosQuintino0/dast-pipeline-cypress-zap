"""
CLI to run the OWASP ZAP scan.

Usage:
    python -m security_tests.cli.run_scan

This script runs the complete security scan pipeline:
1. Connects to ZAP (must be running)
2. Creates a clean session
3. Configures mode and context
4. Imports the filtered HAR
5. Waits for passive scan
6. Configures active scan policy
7. Loads tokenization script
8. Runs active scan endpoint by endpoint
9. Generates HTML report

PREREQUISITES:
- OWASP ZAP must be running (GUI or daemon)
- filtered_traffic.har file must exist
  (run python -m security_tests.cli.process_har first)
- ZAP API key configured in .env
"""

from loguru import logger

from security_tests.config import assert_target_is_allowed, settings
from security_tests.zap_scan.zap_client import (
    create_zap_client,
    test_connection,
    create_clean_session,
    ensure_zap_mode,
)
from security_tests.zap_scan.context import apply_technology_allowlist
from security_tests.zap_scan.scan_policy import (
    configure_scan_policy,
    configure_ascan_options,
)
from security_tests.zap_scan.script_randomizer import load_and_enable_script
from security_tests.zap_scan.scan_execution import (
    get_context_id,
    run_scan_on_endpoint,
)
from security_tests.zap_scan.report import (
    generate_html_report,
    display_alert_summary,
)
from security_tests.har.zap_integration import (
    validate_har_file,
    import_har_into_zap,
    wait_for_passive_scan,
    extract_targets_from_har,
)


def main() -> None:
    """Main security scan pipeline."""
    logger.info("=" * 60)
    logger.info("STARTING DAST SECURITY SCAN")
    logger.info("=" * 60)

    # === PHASE 0: Safety guard ===
    # Runs before anything touches the network. An active scan fires real
    # attack payloads, so pointing this pipeline at a host that is not yours
    # is the difference between a security exercise and an incident. A typo in
    # one environment variable is enough to cross that line, which is why the
    # check is here and not in a README warning.
    assert_target_is_allowed(settings.TARGET_URL)
    assert_target_is_allowed(settings.TARGET_URL_FROM_ZAP)
    logger.info(f"Target allowed: {settings.TARGET_URL}")

    # === PHASE 1: Connection and Setup ===
    logger.info("--- PHASE 1: Connection and Setup ---")

    zap = create_zap_client()
    test_connection(zap)
    create_clean_session(zap)
    ensure_zap_mode(zap)

    # === PHASE 2: Context and Scope ===
    logger.info("--- PHASE 2: Context and Scope ---")

    context_id = apply_technology_allowlist(zap)

    # === PHASE 3: Import HAR ===
    logger.info("--- PHASE 3: Import HAR ---")

    har_path = validate_har_file()
    import_har_into_zap(zap, har_path)

    # === PHASE 4: Passive Scan ===
    logger.info("--- PHASE 4: Passive Scan ---")

    wait_for_passive_scan(zap)

    # === PHASE 5: Configure Active Scan ===
    logger.info("--- PHASE 5: Configure Active Scan ---")

    configure_scan_policy(zap)
    configure_ascan_options(zap)
    load_and_enable_script(zap)

    # === PHASE 6: Active Scan ===
    logger.info("--- PHASE 6: Active Scan ---")

    targets = extract_targets_from_har(har_path)
    context_id_str = get_context_id(zap)

    for i, (url, method, body, url_display) in enumerate(targets, 1):
        logger.info(f"Endpoint {i}/{len(targets)}")
        run_scan_on_endpoint(
            zap=zap,
            url=url,
            method=method,
            body=body,
            url_display=f"{method} {url_display}",
            context_id=context_id_str,
        )

    # === PHASE 7: Report ===
    logger.info("--- PHASE 7: Report ---")

    display_alert_summary(zap)
    report_path = generate_html_report(zap)

    logger.info("=" * 60)
    logger.info("SCAN COMPLETE!")
    logger.info(f"  Report: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
