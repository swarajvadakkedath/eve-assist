"""AIOS entry point."""

import uvicorn
from aios.api.app import create_app
from aios.config.settings import AiosSettings

app = create_app()


def main():
    settings = AiosSettings()
    uvicorn.run(
        "aios.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
