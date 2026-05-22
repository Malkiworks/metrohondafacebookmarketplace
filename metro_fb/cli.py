from __future__ import annotations

import json
from pathlib import Path

import click

from metro_fb.config import load_config
from metro_fb.export_web import export_web_data
from metro_fb.facebook_listing import write_listing_pack
from metro_fb.photos import download_vehicle_photos
from metro_fb.scrape import scrape_vehicle_urls
from metro_fb.sitemap import fetch_sitemap_urls, filter_vehicle_urls

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
INVENTORY_FILE = DATA_DIR / "inventory.json"


@click.group()
def cli():
    """Scrape Metro Honda inventory and build Facebook Marketplace listing packs."""


@cli.command("scrape")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--limit", type=int, default=None, help="Override max_vehicles from config")
def scrape_cmd(config_path: Path | None, limit: int | None):
    """Fetch vehicle details from mymetrohonda.com (Jersey City sitemap)."""
    config = load_config(config_path)
    scrape_cfg = config.get("scrape", {})

    click.echo("Loading sitemap...")
    urls = fetch_sitemap_urls(scrape_cfg.get("sitemap_url", ""))
    urls = filter_vehicle_urls(
        urls,
        condition=scrape_cfg.get("condition", "used"),
        make_filter=scrape_cfg.get("make_filter"),
    )
    click.echo(f"Found {len(urls)} matching vehicles.")

    max_v = limit or scrape_cfg.get("max_vehicles")
    if max_v:
        urls = urls[: int(max_v)]

    def progress(i: int, total: int, url: str):
        click.echo(f"[{i}/{total}] {url}")

    vehicles = scrape_vehicle_urls(
        urls,
        delay_seconds=float(scrape_cfg.get("delay_seconds", 2)),
        on_progress=progress,
    )

    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "count": len(vehicles),
        "vehicles": [v.to_dict() for v in vehicles],
    }
    INVENTORY_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    click.echo(f"Saved {len(vehicles)} vehicles to {INVENTORY_FILE}")


@cli.command("build")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--download-photos/--no-photos", default=None)
def build_cmd(config_path: Path | None, download_photos: bool | None):
    """Create Facebook Marketplace copy/paste packs from scraped inventory."""
    if not INVENTORY_FILE.exists():
        raise click.ClickException("Run `scrape` first — no data/inventory.json found.")

    config = load_config(config_path)
    scrape_cfg = config.get("scrape", {})
    do_photos = (
        download_photos
        if download_photos is not None
        else scrape_cfg.get("download_photos", True)
    )
    max_photos = int(scrape_cfg.get("max_photos_per_vehicle", 20))

    data = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(exist_ok=True)

    from metro_fb.models import Vehicle

    for raw in data.get("vehicles", []):
        vehicle = Vehicle(**raw)
        photo_paths: list[Path] = []
        if do_photos and vehicle.image_urls:
            cache = DATA_DIR / "photos" / vehicle.slug()
            photo_paths = download_vehicle_photos(
                vehicle.slug(),
                vehicle.image_urls,
                cache,
                max_photos=max_photos,
            )
        pack = write_listing_pack(vehicle, config, OUTPUT_DIR, photo_paths=photo_paths)
        click.echo(f"Built {pack}")

    click.echo(f"Done. Open {OUTPUT_DIR} and use each folder's LISTING.txt on Marketplace.")


@cli.command("run")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--limit", type=int, default=None)
def run_cmd(config_path: Path | None, limit: int | None):
    """Scrape inventory and build listing packs in one step."""
    ctx = click.get_current_context()
    ctx.invoke(scrape_cmd, config_path=config_path, limit=limit)
    ctx.invoke(build_cmd, config_path=config_path, download_photos=None)


@cli.command("export-web")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--no-photos", is_flag=True, help="Skip downloading photos to public/")
def export_web_cmd(config_path: Path | None, no_photos: bool):
    """Export inventory + photos to public/ for the static website."""
    config = load_config(config_path)
    path = export_web_data(config, download_photos=not no_photos)
    click.echo(f"Web data ready: {path}")


if __name__ == "__main__":
    cli()
