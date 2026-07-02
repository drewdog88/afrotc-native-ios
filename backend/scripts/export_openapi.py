"""Export the FastAPI OpenAPI spec to shared/openapi.json.

This JSON is the single shared contract: the web app generates a TypeScript
client from it and the iOS app generates Swift models from it. Re-run whenever
the API surface changes:

    uv run python scripts/export_openapi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the backend package importable when run as a bare script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

# backend/scripts/ -> repo root -> shared/
OUT = Path(__file__).resolve().parents[2] / "shared" / "openapi.json"


def main() -> None:
    spec = app.openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    paths = spec.get("paths", {})
    print(f"Wrote {OUT} ({len(paths)} paths, OpenAPI {spec.get('openapi')})")


if __name__ == "__main__":
    main()
