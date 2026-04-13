"""Configuration for CrawlFeasibility"""
import sys
import logging

VERSION = "1.0.0"

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 2

BASIC_MODE_MAX_REQUESTS = 10
DEEP_MODE_MAX_REQUESTS = 50

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )


def check_environment():
    """Check if the environment is properly configured"""
    issues = []

    if sys.version_info < (3, 8):
        issues.append(f"需要 Python 3.8+, 当前 {sys.version_info.major}.{sys.version_info.minor}")
    else:
        print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}")

    required_packages = [
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
        ("tldextract", "tldextract"),
        ("rich", "rich"),
        ("pydantic", "pydantic"),
    ]

    for pkg_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"[OK] {pkg_name} - installed")
        except ImportError:
            print(f"[X] {pkg_name} - not installed")
            issues.append(f"Please run: pip install {pkg_name}")

    return len(issues) == 0, issues
