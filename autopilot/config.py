"""Load config.toml and profile.toml (see the *.example.toml files)."""
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    path = ROOT / name
    if not path.exists():
        example = name.replace(".toml", ".example.toml")
        sys.exit(f"{name} not found. Copy {example} to {name} and edit it.")
    with path.open("rb") as f:
        return tomllib.load(f)


def load_config():
    cfg = _load("config.toml")
    paths = cfg.setdefault("paths", {})
    out = Path(paths.get("output_dir", "output")).expanduser()
    paths["output_dir"] = out if out.is_absolute() else ROOT / out
    paths["status_import_dir"] = Path(paths.get("status_import_dir", "~/Downloads")).expanduser()
    return cfg


def load_profile():
    return _load("profile.toml")
