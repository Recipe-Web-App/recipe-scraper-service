"""Script to run the application in the local configuration."""

import uvicorn


def main() -> None:
    """Run the server in local configuration."""
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
