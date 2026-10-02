"""Loads config/config.yaml so every module reads settings from one place."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path="config/config.yaml") -> dict:
    """Return the YAML config as a dict. Relative paths resolve from the project root."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
