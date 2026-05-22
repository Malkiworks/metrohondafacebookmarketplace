from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from metro_fb.config import load_config
from metro_fb.export_web import export_web_data
from metro_fb.models import Vehicle
from metro_fb.scrape import fetch_vehicle
from metro_fb.sitemap import fetch_sitemap_urls, filter_vehicle_urls

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
INVENTORY_FILE = DATA_DIR / "inventory.json"
WEB_INVENTORY = PROJECT_ROOT / "public" / "data" / "inventory.json"


class InventoryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._refresh_thread: threading.Thread | None = None
        self.last_error: str | None = None
        self.last_refresh_started_at: str | None = None
        self.last_refresh_finished_at: str | None = None
        self.refresh_completed = 0
        self.refresh_total = 0
        self.refresh_stage = "idle"

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
        inventory["refreshCompleted"] = self.refresh_completed
        inventory["refreshTotal"] = self.refresh_total
        inventory["refreshStage"] = self.refresh_stage
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
        self.last_refresh_finished_at = None
        self.refresh_completed = 0
        self.refresh_total = 0
        self.refresh_stage = "loading sitemap"
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

            self.refresh_total = len(urls)
            self.refresh_stage = "showing sitemap vehicles"
            vehicles_by_key = {
                self._vehicle_key(vehicle): vehicle
                for vehicle in [self._vehicle_from_url(url) for url in urls]
            }
            self._write_inventory(list(vehicles_by_key.values()))
            export_web_data(config, download_photos=False)

            workers = int(scrape_cfg.get("workers", 12))
            self.refresh_stage = "loading prices and photos"
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_url = {executor.submit(fetch_vehicle, url): url for url in urls}
                for future in as_completed(future_to_url):
                    self.refresh_completed += 1
                    url = future_to_url[future]
                    try:
                        vehicle = future.result()
                    except Exception:
                        vehicle = None
                    if vehicle:
                        vehicles_by_key[self._vehicle_key(vehicle)] = vehicle
                    elif url:
                        placeholder = self._vehicle_from_url(url)
                        vehicles_by_key.setdefault(
                            self._vehicle_key(placeholder), placeholder
                        )

                    # Keep the UI live without thrashing the disk on every single car.
                    if (
                        self.refresh_completed == self.refresh_total
                        or self.refresh_completed % 5 == 0
                    ):
                        self._write_inventory(list(vehicles_by_key.values()))
                        export_web_data(config, download_photos=False)

            self._write_inventory(list(vehicles_by_key.values()))
            export_web_data(config, download_photos=False)
            self.refresh_stage = "complete"
            self.last_refresh_finished_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:  # keep API alive if the dealer site fails
            self.last_error = str(exc)
            self.refresh_stage = "error"

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

    def _vehicle_key(self, vehicle: Vehicle) -> str:
        return vehicle.listing_id or vehicle.vin or vehicle.url

    def _vehicle_from_url(self, url: str) -> Vehicle:
        listing_match = re.search(r"/(\d+)/?$", url)
        listing_id = listing_match.group(1) if listing_match else url
        slug_match = re.search(r"/auto/([^/]+)/", url)
        slug = slug_match.group(1) if slug_match else "used-honda"
        parts = slug.split("-")
        if parts and parts[0] in {"used", "new", "certified"}:
            condition = parts.pop(0)
        else:
            condition = "used"

        year = 0
        if parts and parts[0].isdigit():
            year = int(parts.pop(0))

        stop_words = {"near", "jersey", "city", "nj"}
        clean_parts: list[str] = []
        for part in parts:
            if part in stop_words:
                break
            clean_parts.append(part)

        make = clean_parts[0].title() if clean_parts else "Honda"
        model_parts = clean_parts[1:] if len(clean_parts) > 1 else []
        model = " ".join(p.upper() if len(p) <= 3 else p.title() for p in model_parts)
        title = " ".join(str(x) for x in [condition.title(), year or "", make, model] if x)

        return Vehicle(
            listing_id=listing_id,
            url=url,
            vin="",
            year=year,
            make=make,
            model=model,
            trim="",
            title=title,
            condition=condition,
            price=0,
            mileage=0,
            exterior_color="",
            interior_color="",
            transmission="",
            engine="",
            body_style="",
            drivetrain="",
            fuel_type="",
            mpg="",
            stock_number="",
            image_urls=[],
            features=[],
            dealer_url=url,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )


cache = InventoryCache()
