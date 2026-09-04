"""
ZAP active scan policy configuration.

The policy defines HOW ZAP attacks the endpoints:
- Attack Strength: how many payload variations to send
- Alert Threshold: minimum confidence level to report
- Threads: how many simultaneous requests
- Delay: interval between requests (rate limiting)

TIP: For public APIs, use MEDIUM strength and LOW threshold.
INSANE strength can take HOURS on a single URL.
"""

from loguru import logger
from zapv2 import ZAPv2  # type: ignore[import-untyped]

from security_tests.config import settings


def configure_scan_policy(zap: ZAPv2) -> None:
    """
    Configures attack strength and alert sensitivity
    on ZAP's default policy.

    The "Default Policy" is used if no custom policy
    is specified when starting the scan.
    """
    policy = "Default Policy"

    # Configure attack strength for ALL scanners
    zap.ascan.set_policy_attack_strength(
        id=0,  # 0 = all scanners
        attackstrength=settings.ZAP_ATTACK_STRENGTH.value,
        scanpolicyname=policy,
    )
    logger.info(f"Attack Strength: {settings.ZAP_ATTACK_STRENGTH.value}")

    # Configure alert threshold
    zap.ascan.set_policy_alert_threshold(
        id=0,
        alertthreshold=settings.ZAP_ALERT_THRESHOLD.value,
        scanpolicyname=policy,
    )
    logger.info(f"Alert Threshold: {settings.ZAP_ALERT_THRESHOLD.value}")


def configure_ascan_options(zap: ZAPv2) -> None:
    """
    Configures advanced active scan options.

    - injectable params: which parameters ZAP should try to inject
    - scan headers: test injection in HTTP headers
    - add query params: add extra parameters for testing
    - thread per host: parallelism (careful with rate limiting!)
    - delay: interval between requests in ms
    """
    zap.ascan.set_option_target_params_injectable(15)  # All params
    zap.ascan.set_option_scan_headers_all_requests(True)
    zap.ascan.set_option_add_query_param(True)
    zap.ascan.set_option_thread_per_host(settings.ZAP_THREAD_PER_HOST)
    zap.ascan.set_option_delay_in_ms(settings.ZAP_DELAY_IN_MS)

    logger.info(
        f"Scan options: threads={settings.ZAP_THREAD_PER_HOST}, delay={settings.ZAP_DELAY_IN_MS}ms"
    )
