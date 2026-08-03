"""AIOS entry point."""

import os

import uvicorn
from aios.api.app import create_app
from aios.config.settings import AiosSettings

app = create_app()


def main():
    settings = AiosSettings()
    reload = os.environ.get("EVE_ENV", "").lower() in ("dev", "development")
    uvicorn.run(
        "aios.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
