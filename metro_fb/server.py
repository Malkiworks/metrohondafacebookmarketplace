from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from metro_fb.config import load_config
from metro_fb.live_cache import cache

PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="Metro Honda Marketplace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    # Show cached inventory instantly; refresh in the background if stale/missing.
    cache.refresh_async(force=False)


@app.get("/api/inventory")
def inventory() -> dict:
    cache.refresh_async(force=False)
    return cache.read_api_payload()


@app.get("/api/config")
def config() -> dict:
    cfg = load_config()
    return {
        "seller": cfg.get("seller", {}),
        "dealer": cfg.get("dealer", {}),
        "facebook": cfg.get("facebook", {}),
    }


@app.post("/api/refresh")
def refresh() -> dict:
    started = cache.refresh_async(force=True)
    payload = cache.read_api_payload()
    payload["refreshStarted"] = started
    return payload


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "refreshing": cache.refreshing}


dist = PROJECT_ROOT / "dist"
assets = dist / "assets"
if assets.exists():
    app.mount("/assets", StaticFiles(directory=assets), name="assets")

public_data = PROJECT_ROOT / "public" / "data"
if public_data.exists():
    app.mount("/data", StaticFiles(directory=public_data), name="data")


@app.get("/{path:path}", response_model=None)
def spa(path: str):
    index = dist / "index.html"
    file_path = dist / path
    if path and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    if index.exists():
        return FileResponse(index)
    return {
        "detail": "Frontend build not found. Run `npm run build` before starting the server."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    args = parser.parse_args()
    uvicorn.run("metro_fb.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
