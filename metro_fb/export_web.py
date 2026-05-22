from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from metro_fb.config import load_config
from metro_fb.facebook_listing import build_listing_payload
from metro_fb.models import Vehicle
from metro_fb.photos import download_vehicle_photos

PUBLIC_DIR = Path("public")
DATA_DIR = Path("data")
INVENTORY_FILE = DATA_DIR / "inventory.json"
WEB_INVENTORY = PUBLIC_DIR / "data" / "inventory.json"
WEB_CONFIG = PUBLIC_DIR / "site-config.json"
WEB_PHOTOS = PUBLIC_DIR / "data" / "photos"


def export_web_data(
    config: dict[str, Any],
    *,
    source_inventory: Path | None = None,
    download_photos: bool = True,
    max_photos: int = 20,
) -> Path:
    inv_path = source_inventory or INVENTORY_FILE
    if not inv_path.exists():
        raise FileNotFoundError(
            f"No inventory at {inv_path}. Run: python -m metro_fb scrape"
        )

    raw = json.loads(inv_path.read_text(encoding="utf-8"))
    scrape_cfg = config.get("scrape", {})
    do_photos = download_photos if download_photos is not None else scrape_cfg.get(
        "download_photos", True
    )
    max_photos = int(scrape_cfg.get("max_photos_per_vehicle", max_photos))

    PUBLIC_DIR.mkdir(exist_ok=True)
    WEB_PHOTOS.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / "data").mkdir(exist_ok=True)

    seller = config.get("seller", {})
    dealer = config.get("dealer", {})
    WEB_CONFIG.write_text(
        json.dumps(
            {
                "seller": seller,
                "dealer": dealer,
                "facebook": config.get("facebook", {}),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    listings: list[dict[str, Any]] = []

    for item in raw.get("vehicles", []):
        vehicle = Vehicle(**item)
        marketplace = build_listing_payload(vehicle, config)

        local_photos: list[str] = []
        if do_photos and vehicle.image_urls:
            photo_dir = WEB_PHOTOS / vehicle.slug()
            if photo_dir.exists():
                shutil.rmtree(photo_dir)
            paths = download_vehicle_photos(
                vehicle.slug(),
                vehicle.image_urls,
                photo_dir,
                max_photos=max_photos,
            )
            local_photos = [
                f"/data/photos/{vehicle.slug()}/{p.name}" for p in paths
            ]

        listings.append(
            {
                "id": vehicle.vin or vehicle.listing_id,
                "vehicle": vehicle.to_dict(),
                "marketplace": marketplace,
                "photos": local_photos,
                "photoUrls": vehicle.image_urls[:max_photos],
            }
        )

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(listings),
        "listings": listings,
    }
    WEB_INVENTORY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return WEB_INVENTORY
