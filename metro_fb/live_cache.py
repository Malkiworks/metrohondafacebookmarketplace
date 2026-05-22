from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from metro_fb.config import load_config
from metro_fb.export_web import export_web_data
from metro_fb.models import Vehicle
from metro_fb.scrape import scrape_vehicle_urls_fast
from metro_fb.sitemap import fetch_sitemap_urls, filter_vehicle_urls

DATA_DIR = Path("data")
INVENTORY_FILE = DATA_DIR / "inventory.json"
WEB_INVENTORY = Path("public/data/inventory.json")


class InventoryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._refresh_thread: threading.Thread | None = None
        self.last_error: str | None = None
        self.last_refresh_started_at: str | None = None
        self.last_refresh_finished_at: str | None = None

    @property
    def refreshing(self) -> bool:
        return bool(self._refresh_thread and self._refresh_thread.is_alive())

    def read_web_inventory(self) -> dict[str, Any] | None:
        if not WEB_INVENTORY.exists():
            return None
        try:
            return json.loads(WEB_INVENTORY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def read_api_payload(self) -> dict[str, Any]:
        inventory = self.read_web_inventory()
        if not inventory:
            inventory = {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "count": 0,
                "listings": [],
            }

        inventory["refreshing"] = self.refreshing
        inventory["lastError"] = self.last_error
        inventory["lastRefreshStartedAt"] = self.last_refresh_started_at
        inventory["lastRefreshFinishedAt"] = self.last_refresh_finished_at
        return inventory

    def is_stale(self, max_age_minutes: int) -> bool:
        inventory = self.read_web_inventory()
        if not inventory:
            return True
        generated = inventory.get("generatedAt")
        if not generated:
            return True
        try:
            generated_at = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        except ValueError:
            return True
        return datetime.now(timezone.utc) - generated_at > timedelta(
            minutes=max_age_minutes
        )

    def refresh_async(self, *, force: bool = False) -> bool:
        with self._lock:
            if self.refreshing:
                return False
            if not force and not self.is_stale(max_age_minutes=20):
                return False
            self._refresh_thread = threading.Thread(
                target=self.refresh_now,
                name="inventory-refresh",
                daemon=True,
            )
            self._refresh_thread.start()
            return True

    def refresh_now(self) -> None:
        self.last_error = None
        self.last_refresh_started_at = datetime.now(timezone.utc).isoformat()
        try:
            config = load_config()
            scrape_cfg = config.get("scrape", {})
            urls = fetch_sitemap_urls(scrape_cfg.get("sitemap_url", ""))
            urls = filter_vehicle_urls(
                urls,
                condition=scrape_cfg.get("condition", "used"),
                make_filter=scrape_cfg.get("make_filter"),
            )
            max_v = scrape_cfg.get("max_vehicles")
            if max_v:
                urls = urls[: int(max_v)]

            workers = int(scrape_cfg.get("workers", 12))
            vehicles = scrape_vehicle_urls_fast(urls, max_workers=workers)
            self._write_inventory(vehicles)
            export_web_data(config, download_photos=False)
            self.last_refresh_finished_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:  # keep API alive if the dealer site fails
            self.last_error = str(exc)

    def _write_inventory(self, vehicles: list[Vehicle]) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        INVENTORY_FILE.write_text(
            json.dumps(
                {
                    "count": len(vehicles),
                    "vehicles": [vehicle.to_dict() for vehicle in vehicles],
                },
                indent=2,
            ),
            encoding="utf-8",
        )


cache = InventoryCache()
