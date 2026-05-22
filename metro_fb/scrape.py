from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

from bs4 import BeautifulSoup
from curl_cffi import requests

from metro_fb.models import Vehicle

LISTING_ID_RE = re.compile(r"/(\d+)/?$")


def _first_offer(car: dict[str, Any]) -> dict[str, Any]:
    offers = car.get("offers") or []
    if isinstance(offers, list) and offers:
        return offers[0] if isinstance(offers[0], dict) else {}
    if isinstance(offers, dict):
        return offers
    return {}


def _num(value: Any) -> int | float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return None


def _parse_financing(offer: dict[str, Any], vin: str, price: int) -> dict[str, Any]:
    methods = offer.get("acceptedPaymentMethod") or []
    if isinstance(methods, dict):
        methods = [methods]
    if not isinstance(methods, list) or not methods:
        return {}

    method = next((m for m in methods if isinstance(m, dict)), None)
    if not method:
        return {}

    repayment = method.get("loanRepaymentForm") or {}
    amount = method.get("amount") or {}
    loan_term = method.get("loanTerm") or {}
    apr = method.get("annualPercentageRate") or {}
    down_payment = repayment.get("downPayment") or {}
    monthly = repayment.get("loanPaymentAmount") or {}

    monthly_payment = _num(monthly.get("value"))
    term_months = _num(loan_term.get("value"))
    amount_financed = _num(amount.get("value"))
    apr_value = _num(apr.get("value"))
    due_at_signing = _num(down_payment.get("value"))

    if not any([monthly_payment, term_months, amount_financed, apr_value, due_at_signing]):
        return {}

    return {
        "monthly_payment": monthly_payment,
        "term_months": term_months,
        "due_at_signing": due_at_signing,
        "apr": apr_value,
        "amount_financed": amount_financed,
        "selling_price": price or None,
        "provider": "Honda Financial Services",
        "credit_score": 800,
        "vin": vin,
    }


def _mileage(car: dict[str, Any]) -> int:
    odo = car.get("mileageFromOdometer") or {}
    if isinstance(odo, dict):
        try:
            return int(odo.get("value") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def _mpg(car: dict[str, Any]) -> str:
    fe = car.get("fuelEfficiency") or {}
    if isinstance(fe, dict) and fe.get("value"):
        unit = fe.get("unitText") or "MPG"
        return f"{fe['value']} {unit}"
    return ""


def _brand_name(car: dict[str, Any]) -> str:
    brand = car.get("brand") or car.get("manufacturer") or {}
    if isinstance(brand, dict):
        return str(brand.get("name") or "Honda")
    return "Honda"


def _condition_from_slug_and_offer(slug: str, offer: dict[str, Any]) -> str:
    slug_l = slug.lower()
    if "certified" in slug_l or "cpo" in slug_l:
        return "certified"
    item = str(offer.get("itemCondition") or "")
    if "Used" in item:
        return "used"
    if "New" in item:
        return "new"
    if slug_l.startswith("used-"):
        return "used"
    if slug_l.startswith("new-"):
        return "new"
    return "used"


def _parse_features(soup: BeautifulSoup) -> list[str]:
    features: list[str] = []
    selectors = [
        ".equipment-list li",
        ".features-list li",
        ".vehicle-features li",
        "[data-testid='features'] li",
        ".vdp-features li",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            text = el.get_text(strip=True)
            if text and len(text) < 120 and text not in features:
                features.append(text)
        if features:
            break
    return features[:40]


def _parse_body_and_drivetrain(soup: BeautifulSoup, html: str) -> tuple[str, str, str]:
    body, drive, fuel = "", "", ""
    for row in soup.select(".spec-list li, .specifications li, dl.key-value dt"):
        label = row.get_text(strip=True).lower()
        parent = row.find_parent()
        value_el = row.find_next_sibling() if row.name == "dt" else row
        value = value_el.get_text(strip=True) if value_el else ""
        if "body" in label:
            body = value
        elif "drive" in label:
            drive = value
        elif "fuel" in label:
            fuel = value

    if not body:
        m = re.search(r'"bodyType"\s*:\s*"([^"]+)"', html)
        if m:
            body = m.group(1)
    if not drive:
        m = re.search(r'"driveWheelConfiguration"\s*:\s*"([^"]+)"', html)
        if m:
            drive = m.group(1)
    return body, drive, fuel


def _first_value(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if isinstance(value, list) and value:
        return str(value[0] or "")
    return str(value or "")


def _parse_dep_page_data(html: str) -> dict[str, Any] | None:
    match = re.search(r"depEventPublisher\.setPageData\((\{.*?\})\);", html, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _parse_fallback_vehicle(url: str, html: str, soup: BeautifulSoup) -> Vehicle | None:
    data = _parse_dep_page_data(html)
    if not data:
        return None

    listing_match = LISTING_ID_RE.search(url)
    listing_id = listing_match.group(1) if listing_match else _first_value(data, "vehicle_id")
    year = int(_first_value(data, "vehicle_year") or 0)
    make = _first_value(data, "vehicle_make") or "Honda"
    model = _first_value(data, "vehicle_model")
    trim = _first_value(data, "vehicle_trim")
    title = f"Used {year} {make} {model} {trim}".strip()

    raw_price = _first_value(data, "vehicle_price")
    try:
        price = int(float(raw_price)) if raw_price else 0
    except ValueError:
        price = 0

    image_urls: list[str] = []
    for img in soup.select('img[data-src*="cloudflareimages"]'):
        src = img.get("data-src")
        if src and src not in image_urls:
            image_urls.append(src)

    body, drivetrain, fuel_type = _parse_body_and_drivetrain(soup, html)
    fuel_type = str(car.get("fuelType") or fuel_type or "")
    body = body or _first_value(data, "vehicle_body_style")
    fuel_type = fuel_type or _first_value(data, "vehicle_engine_fuel")

    return Vehicle(
        listing_id=listing_id,
        url=url,
        vin=_first_value(data, "vehicle_vin"),
        year=year,
        make=make,
        model=model,
        trim=trim,
        title=title,
        condition="used",
        price=price,
        mileage=0,
        exterior_color=_first_value(data, "vehicle_color_ext"),
        interior_color=_first_value(data, "vehicle_color_int"),
        transmission=_first_value(data, "vehicle_transmission"),
        engine=_first_value(data, "vehicle_engine"),
        body_style=body,
        drivetrain=drivetrain,
        fuel_type=fuel_type,
        mpg="",
        stock_number=_first_value(data, "vehicle_stock"),
        image_urls=image_urls,
        features=_parse_features(soup),
        financing={},
        dealer_url=url,
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )


def parse_vehicle_page(url: str, html: str) -> Vehicle | None:
    soup = BeautifulSoup(html, "lxml")
    car: dict[str, Any] | None = None

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "Car":
            car = data
            break
        if isinstance(data, dict) and "@graph" in data:
            for node in data["@graph"]:
                if isinstance(node, dict) and node.get("@type") == "Car":
                    car = node
                    break
        if car:
            break

    if not car:
        return _parse_fallback_vehicle(url, html, soup)

    offer = _first_offer(car)
    listing_match = LISTING_ID_RE.search(url)
    listing_id = listing_match.group(1) if listing_match else ""

    slug_match = re.search(r"/auto/([^/]+)/", url)
    slug = slug_match.group(1) if slug_match else ""

    year = int(car.get("releaseDate") or car.get("vehicleModelDate") or 0)
    price = int(offer.get("price") or 0)
    vin = str(car.get("vehicleIdentificationNumber") or car.get("mpn") or "")
    images = car.get("image") or []
    if isinstance(images, str):
        images = [images]

    body, drivetrain, fuel_type = _parse_body_and_drivetrain(soup, html)
    engine_block = car.get("vehicleEngine") or {}
    engine = ""
    if isinstance(engine_block, dict):
        engine = str(engine_block.get("name") or "")

    rel_url = str(car.get("url") or "")
    dealer_url = url if url.startswith("http") else f"https://www.mymetrohonda.com{rel_url}"

    return Vehicle(
        listing_id=listing_id,
        url=dealer_url,
        vin=vin,
        year=year,
        make=_brand_name(car),
        model=str(car.get("model") or ""),
        trim=str(car.get("vehicleConfiguration") or ""),
        title=str(car.get("name") or "").strip(),
        condition=_condition_from_slug_and_offer(slug, offer),
        price=price,
        mileage=_mileage(car),
        exterior_color=str(car.get("color") or ""),
        interior_color=str(car.get("vehicleInteriorColor") or ""),
        transmission=str(car.get("vehicleTransmission") or ""),
        engine=engine,
        body_style=body,
        drivetrain=drivetrain,
        fuel_type=fuel_type,
        mpg=_mpg(car),
        stock_number=str(car.get("sku") or ""),
        image_urls=[u for u in images if isinstance(u, str)],
        features=_parse_features(soup),
        financing=_parse_financing(offer, vin, price),
        dealer_url=dealer_url,
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )


def scrape_vehicle_urls(
    urls: list[str],
    *,
    delay_seconds: float = 2.0,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[Vehicle]:
    vehicles: list[Vehicle] = []
    total = len(urls)

    for index, url in enumerate(urls, start=1):
        if on_progress:
            on_progress(index, total, url)
        try:
            response = requests.get(url, impersonate="chrome120", timeout=45)
            if response.status_code != 200:
                continue
            vehicle = parse_vehicle_page(url, response.text)
            if vehicle and vehicle.price > 0:
                vehicles.append(vehicle)
        except Exception:
            continue
        if index < total and delay_seconds > 0:
            time.sleep(delay_seconds)

    return vehicles


def fetch_vehicle(url: str) -> Vehicle | None:
    """Fetch and parse one VDP."""
    response = requests.get(url, impersonate="chrome120", timeout=45)
    if response.status_code != 200:
        return None
    return parse_vehicle_page(url, response.text)


def scrape_vehicle_urls_fast(
    urls: list[str],
    *,
    max_workers: int = 10,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[Vehicle]:
    """Fetch VDPs concurrently for background cache refreshes."""
    vehicles: list[Vehicle] = []
    total = len(urls)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_vehicle, url): url for url in urls}
        for future in as_completed(future_to_url):
            completed += 1
            url = future_to_url[future]
            if on_progress:
                on_progress(completed, total, url)
            try:
                vehicle = future.result()
            except Exception:
                continue
            if vehicle:
                vehicles.append(vehicle)

    vehicles.sort(key=lambda v: (v.year, v.make, v.model, v.trim), reverse=True)
    return vehicles
