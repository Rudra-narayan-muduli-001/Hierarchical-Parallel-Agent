from pathlib import Path

import yaml

from hierarchy.config.models import Config


def load_config(path: str = "config/config.yaml") -> Config:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path_obj, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ValueError(f"Config file is empty: {path}")
    return Config(**raw)
