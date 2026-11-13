from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]   # src/paths.py → parents[0] = src, parents[1] = coolsite

DATA = PROJECT_ROOT / "data"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
QUARANTINE = DATA / "quarantine"
GOLD = DATA / "gold" / "cooling_modes"
LOGS = PROJECT_ROOT / "logs"