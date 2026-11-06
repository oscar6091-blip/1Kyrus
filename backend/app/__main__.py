"""`python -m app` — start the API with BACKEND_HOST/BACKEND_PORT from `.env`.

One process, no auto-reload, no extra workers (state recovery rules depend on it).
"""
import uvicorn

from .config import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.backend_host, port=settings.backend_port, reload=False, workers=1)
