from __future__ import annotations

from pathlib import Path

import yaml

from site_scraper.models import SiteConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SITES_ROOT = PROJECT_ROOT / "sites"
RUNS_ROOT = PROJECT_ROOT / "runs"
GENERATED_ROOT = PROJECT_ROOT / "generated_sites"


def site_config_path(name: str) -> Path:
    return SITES_ROOT / name / "site.yaml"


def load_site(name: str) -> SiteConfig:
    path = site_config_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Missing site config: {path}")
    return SiteConfig.model_validate(yaml.safe_load(path.read_text()))


def save_site(config: SiteConfig) -> Path:
    path = site_config_path(config.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False))
    return path
