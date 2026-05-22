from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from metro_fb.models import Vehicle


def build_marketplace_title(vehicle: Vehicle) -> str:
    parts = [str(vehicle.year), vehicle.make, vehicle.model]
    if vehicle.trim:
        parts.append(vehicle.trim)
    return " ".join(p for p in parts if p)


def build_marketplace_description(
    vehicle: Vehicle,
    config: dict[str, Any],
) -> str:
    fb_cfg = config.get("facebook", {})
    seller = config.get("seller", {})
    lines: list[str] = []

    lines.append(
        f"{vehicle.year} {vehicle.make} {vehicle.model} {vehicle.trim}".strip()
    )
    lines.append("")
    lines.append(f"Mileage: {vehicle.mileage:,} miles")
    if vehicle.exterior_color:
        lines.append(f"Exterior: {vehicle.exterior_color}")
    if vehicle.interior_color:
        lines.append(f"Interior: {vehicle.interior_color}")
    if vehicle.transmission:
        lines.append(f"Transmission: {vehicle.transmission}")
    if vehicle.engine:
        lines.append(f"Engine: {vehicle.engine}")
    if vehicle.drivetrain:
        lines.append(f"Drivetrain: {vehicle.drivetrain}")
    if vehicle.mpg:
        lines.append(f"Fuel economy: {vehicle.mpg}")

    if vehicle.features:
        lines.append("")
        lines.append("Highlights:")
        for feat in vehicle.features[:12]:
            lines.append(f"• {feat}")

    if fb_cfg.get("include_vin_in_description") and vehicle.vin:
        lines.append("")
        lines.append(f"VIN: {vehicle.vin}")

    contact_method = seller.get("contact_method", "facebook")
    phone = seller.get("phone")
    if contact_method == "phone" and phone:
        lines.append("")
        lines.append(f"Text or call {phone} to schedule a test drive.")
    else:
        lines.append("")
        lines.append("Message me on Facebook to schedule a test drive.")

    footer = fb_cfg.get("footer")
    if footer:
        lines.append("")
        lines.append(footer)

    return "\n".join(lines)


def build_listing_payload(vehicle: Vehicle, config: dict[str, Any]) -> dict[str, Any]:
    seller = config.get("seller", {})
    dealer = config.get("dealer", {})
    fb_cfg = config.get("facebook", {})

    return {
        "title": build_marketplace_title(vehicle),
        "price": vehicle.price,
        "price_formatted": f"${vehicle.price:,}" if vehicle.price else "Contact for price",
        "description": build_marketplace_description(vehicle, config),
        "category": fb_cfg.get("category", "Cars & Trucks"),
        "condition": vehicle.condition,
        "location": {
            "city": seller.get("location_city") or dealer.get("city"),
            "state": seller.get("location_state") or dealer.get("state"),
        },
        "vehicle": {
            "year": vehicle.year,
            "make": vehicle.make,
            "model": vehicle.model,
            "trim": vehicle.trim,
            "mileage": vehicle.mileage,
            "body_style": vehicle.body_style,
            "exterior_color": vehicle.exterior_color,
            "interior_color": vehicle.interior_color,
            "transmission": vehicle.transmission,
            "fuel_type": vehicle.fuel_type,
            "vin": vehicle.vin,
        },
        "photo_count": len(vehicle.image_urls),
        "dealer_reference_url": vehicle.dealer_url,
        "listing_id": vehicle.listing_id,
    }


def write_listing_pack(
    vehicle: Vehicle,
    config: dict[str, Any],
    output_dir: Path,
    *,
    photo_paths: list[Path] | None = None,
) -> Path:
    pack_dir = output_dir / vehicle.slug()
    pack_dir.mkdir(parents=True, exist_ok=True)

    payload = build_listing_payload(vehicle, config)
    (pack_dir / "listing.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    instructions = f"""Facebook Marketplace — copy/paste pack
========================================

TITLE:
{payload['title']}

PRICE:
{payload['price_formatted']}

LOCATION:
{payload['location']['city']}, {payload['location']['state']}

DESCRIPTION:
{payload['description']}

PHOTOS:
Upload images from the photos/ folder (up to 20).
"""
    (pack_dir / "LISTING.txt").write_text(instructions, encoding="utf-8")

    if photo_paths:
        photos_dir = pack_dir / "photos"
        photos_dir.mkdir(exist_ok=True)
        for path in photo_paths:
            dest = photos_dir / path.name
            if path.exists() and not dest.exists():
                dest.write_bytes(path.read_bytes())

    return pack_dir
