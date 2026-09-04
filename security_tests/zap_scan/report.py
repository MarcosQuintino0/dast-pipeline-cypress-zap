"""
HTML vulnerability report generation.

ZAP generates detailed HTML reports containing:
- Executive summary (count by severity)
- Alert list with description
- Evidence (request/response that triggered the alert)
- Remediation recommendations
- References (CWE, OWASP, etc.)

The report is self-contained (a single .html) and can be
opened in any browser.
"""

from datetime import datetime
from pathlib import Path
from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def generate_html_report(zap: ZAPv2) -> Path:
    """
    Generates an HTML report with scan results.

    The filename includes a timestamp for versioning.
    Example: zap_report_2025-01-15_14-30-45.html
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"zap_report_{timestamp}.html"
    path = settings.REPORTS_DIR / filename

    logger.info(f"Generating report: {path}")

    # Generate HTML via ZAP API
    html_report = zap.core.htmlreport()

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_report)

    logger.info(f"Report saved to: {path}")
    return path


def display_alert_summary(zap: ZAPv2) -> None:
    """
    Displays an alert summary in the console.

    Groups alerts by risk (High, Medium, Low, Informational)
    and displays count and alert names.
    """
    alerts = zap.core.alerts()
    logger.info(f"Total alerts: {len(alerts)}")

    # Group by risk
    by_risk: dict[str, set[str]] = {}
    for alert in alerts:
        risk = alert.get("risk", "Informational")
        name = alert.get("alert", "Unknown")
        if risk not in by_risk:
            by_risk[risk] = set()
        by_risk[risk].add(name)

    # Display summary
    order = ["High", "Medium", "Low", "Informational"]
    for risk in order:
        if risk in by_risk:
            names = by_risk[risk]
            logger.info(f"  [{risk}] {len(names)} alert type(s):")
            for name in sorted(names):
                logger.info(f"    - {name}")
