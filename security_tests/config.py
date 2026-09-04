"""
Centralized project configuration using Pydantic Settings.

WHY PYDANTIC SETTINGS?
- Automatic type validation (if ZAP_PORT is "abc" it rejects it)
- Safe default values
- Automatically loads from environment variables and .env
- Enum for restricted values (prevents typos)
- IDE autocomplete

All project configuration lives here.
No other file should have hardcoded values.
"""

from enum import Enum
from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings


class ZapMode(str, Enum):
    """ZAP operating modes.
    - safe: observe only, never attack
    - protect: attack only URLs in scope
    - standard: balanced default mode
    - attack: aggressive mode
    """
    SAFE = "safe"
    PROTECT = "protect"
    STANDARD = "standard"
    ATTACK = "attack"


class ZapAttackStrength(str, Enum):
    """Active scan attack intensity.
    LOW = few payload variations
    INSANE = ALL possible variations (very slow)
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    INSANE = "INSANE"


class ZapAlertThreshold(str, Enum):
    """Alert sensitivity.
    LOW = reports even weak suspicions (more false positives)
    HIGH = reports only with high confidence (fewer alerts)
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Settings(BaseSettings):
    """Global project configuration."""

    # === PATHS ===
    BASE_DIR: Path = Path(__file__).resolve().parent
    ZAP_SCRIPTS_DIR: Path = Path(__file__).resolve().parent / "zap_scripts"
    TRAFFIC_DIR: Path = Path(__file__).resolve().parent / "traffic"
    REPORTS_DIR: Path = Path(__file__).resolve().parent / "reports"

    # === TARGET BASE URL ===
    BASE_URL: str = "https://jsonplaceholder.typicode.com"

    # === ZAP ===
    ZAP_HOST: str = "127.0.0.1"
    ZAP_PORT: int = 8080
    ZAP_API_KEY: str = ""
    ZAP_MODE: ZapMode = ZapMode.STANDARD

    # === SCAN POLICY ===
    ZAP_ATTACK_STRENGTH: ZapAttackStrength = ZapAttackStrength.MEDIUM
    ZAP_ALERT_THRESHOLD: ZapAlertThreshold = ZapAlertThreshold.LOW
    ZAP_THREAD_PER_HOST: int = 2
    ZAP_DELAY_IN_MS: int = 0
    ZAP_PSCAN_TIMEOUT_SECONDS: int = 300

    # === BUSINESS RULES ===
    # Defines which HTTP methods are allowed per endpoint.
    # Endpoints not listed here will be REMOVED during preprocessing.
    # This prevents ZAP from attacking endpoints we don't want to test.
    ENDPOINT_RULES: dict[str, list[str]] = {
        "/posts": ["GET", "POST"],
        "/posts/": ["GET", "PUT", "DELETE"],
        "/comments": ["GET", "POST"],
        "/todos": ["GET", "POST"],
        "/users": ["GET"],
        "/users/": ["GET"],
        "/albums": ["GET"],
        "/albums/": ["GET"],
        "/photos": ["GET"],
    }

    # Fields whose numeric values will be replaced by {{AUTO_INT}}.
    # This allows the ZAP HttpSender script to generate unique values
    # on each request during the scan, avoiding duplicate keys.
    FIELDS_TO_TOKENIZE: list[str] = [
        "userId",
        "id",
        "postId",
    ]

    # === TECHNOLOGY ALLOWLIST ===
    # ZAP has hundreds of scan rules for various technologies.
    # Filtering only relevant technologies drastically reduces scan time
    # and decreases false positives.
    # JSONPlaceholder runs on Node.js, so we focus on JavaScript and web servers.
    ZAP_TECH_ALLOWLIST: str = (
        "Language.JavaScript,"
        "WS.Node,"
        "WS.Express,"
        "WS.Nginx,"
        "OS.Linux,"
        "SCM.Git"
    )

    def model_post_init(self, __context: Any) -> None:
        """Create output directories if they don't exist."""
        self.TRAFFIC_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance - import this object in all modules
settings = Settings()
