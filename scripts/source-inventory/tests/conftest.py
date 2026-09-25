import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CONFIG_DIR = str(FIXTURES_DIR / "config")
THEME_DIR = str(FIXTURES_DIR / "theme")

import pytest  # noqa: E402


@pytest.fixture
def config_dir() -> str:
    return CONFIG_DIR


@pytest.fixture
def theme_dir() -> str:
    return THEME_DIR
