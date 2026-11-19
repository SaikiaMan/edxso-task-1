"""Build a sanitized, reproducible submission archive."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

from signalstack.readiness import readiness


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "submission"


def _included_files() -> list[Path]:
    patterns = (
        "app.py", "README.md", "Dockerfile", "compose.yaml", "requirements.txt",
        ".gitignore", ".dockerignore", ".env.example", ".streamlit/config.toml",
        "signalstack/*.py", "signalstack/schema.sql", "tests/test_*.py",
        "docs/*.md", "docs/signal-stack-demo.webm", "examples/internal_feedback_synthetic.csv",
        "examples/public-demo.json.gz", "evidence/meetuniversity_*.json",
        "data/demo/*-brief.md", "data/demo/status.json", "data/demo/verification_counts.json",
    )
    return sorted(path for pattern in patterns for path in ROOT.glob(pattern) if path.is_file())


def build() -> Path:
    example = dotenv_values(ROOT / ".env.example")
    if any(value for key,value in example.items() if key.endswith("_API_KEY")):
        raise ValueError("Clear API key values from .env.example before packaging")
    OUTPUT.mkdir(exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [path.relative_to(ROOT).as_posix() for path in _included_files()],
        "readiness": readiness(),
        "excluded": ["credentials", "operational databases", "private uploads", "research caches"],
    }
    manifest_path = OUTPUT / "verification-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive = OUTPUT / "signal-stack-submission.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in _included_files():
            bundle.write(path, path.relative_to(ROOT))
        bundle.write(manifest_path, manifest_path.relative_to(ROOT))
    return archive


if __name__ == "__main__":
    print(build())
