from __future__ import annotations

from pathlib import Path

from curl_cffi import requests


def download_vehicle_photos(
    vehicle_slug: str,
    image_urls: list[str],
    dest_dir: Path,
    *,
    max_photos: int = 20,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    for index, url in enumerate(image_urls[:max_photos], start=1):
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        filename = f"{index:02d}{ext}"
        path = dest_dir / filename
        if path.exists():
            saved.append(path)
            continue
        try:
            response = requests.get(url, impersonate="chrome120", timeout=60)
            if response.status_code == 200 and response.content:
                path.write_bytes(response.content)
                saved.append(path)
        except Exception:
            continue

    return saved
