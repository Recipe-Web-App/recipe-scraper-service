"""Script to automatically generate openapi json file."""

import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from app.main import app

openapi_schema = get_openapi(
    title=app.title,
    version=app.version,
    routes=app.routes,
)

with Path.open(Path("docs/openapi.json"), "w") as f:
    json.dump(openapi_schema, f, indent=2)
