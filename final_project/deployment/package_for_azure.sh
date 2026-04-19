#!/usr/bin/env bash
set -euo pipefail

PACKAGE_PATH="${PACKAGE_PATH:-deployment/app.zip}"
rm -f "$PACKAGE_PATH"

python3 - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

base = Path(".").resolve()
package_path = base / "deployment" / "app.zip"
include_roots = [
    "app",
    "templates",
    "static",
    "scripts",
    "deployment",
]
include_files = [
    "requirements.txt",
    "README.md",
    "DECISIONS.md",
    "PROJECT_NOTES.md",
    "TODO.md",
    "ML_MODEL_WRITEUP.md",
    "architecture.md",
    "SUBMISSION_HELPER.md",
    "FINAL_STATUS.md",
    "TEST_REPORT.md",
    ".env.example",
    "artifacts/analytics/dashboard_payload.json",
]
skip_parts = {".venv", ".packages", "__pycache__", "artifacts"}
skip_suffixes = {".pyc"}
skip_relative_paths = {
    Path("deployment/app.zip"),
}

with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as zip_file:
    for rel in include_roots:
        root = base / rel
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if any(part in skip_parts for part in path.parts):
                continue
            if path.suffix in skip_suffixes:
                continue
            if path.relative_to(base) in skip_relative_paths:
                continue
            if path.parent.match("data/db") or path.parent.match("data/uploads"):
                continue
            zip_file.write(path, path.relative_to(base))
    for rel in include_files:
        path = base / rel
        if path.exists():
            zip_file.write(path, path.relative_to(base))
print(package_path)
PY

echo "Created $PACKAGE_PATH"
