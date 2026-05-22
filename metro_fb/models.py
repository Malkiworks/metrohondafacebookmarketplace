from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Vehicle:
    listing_id: str
    url: str
    vin: str
    year: int
    make: str
    model: str
    trim: str
    title: str
    condition: str  # used | new | certified
    price: int
    mileage: int
    exterior_color: str
    interior_color: str
    transmission: str
    engine: str
    body_style: str
    drivetrain: str
    fuel_type: str
    mpg: str
    stock_number: str
    image_urls: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    financing: dict[str, Any] = field(default_factory=dict)
    dealer_url: str = ""
    scraped_at: str = ""

    def slug(self) -> str:
        base = self.vin or self.listing_id
        return "".join(c if c.isalnum() else "_" for c in base)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
