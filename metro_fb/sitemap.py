from __future__ import annotations

import re
from urllib.parse import unquote

import httpx

SITEMAP_INDEX = "https://www.mymetrohonda.com/resrc/xmlsitemap/xml-sitemaps/"
JERSEY_CITY_SITEMAP = (
    "https://www.mymetrohonda.com/resrc/xmlsitemap/"
    "sitemap-inventory-search/jersey_city-nj-07305/"
)

AUTO_URL_RE = re.compile(
    r"https://www\.mymetrohonda\.com/auto/([^/]+)/(\d+)/",
    re.I,
)


def fetch_sitemap_urls(sitemap_url: str) -> list[str]:
    response = httpx.get(
        sitemap_url,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=60,
    )
    response.raise_for_status()
    locs = re.findall(r"<loc>([^<]+)</loc>", response.text)
    return [unquote(loc) for loc in locs]


def filter_vehicle_urls(
    urls: list[str],
    *,
    condition: str = "used",
    make_filter: str | None = "honda",
) -> list[str]:
    """Keep /auto/ detail URLs matching condition and optional make slug."""
    result: list[str] = []
    for url in urls:
        match = AUTO_URL_RE.search(url)
        if not match:
            continue
        slug, _listing_id = match.groups()
        slug_lower = slug.lower()

        if condition == "used" and not (
            slug_lower.startswith("used-") or "used-" in slug_lower
        ):
            continue
        if condition == "new" and not slug_lower.startswith("new-"):
            continue
        if make_filter and make_filter.lower() not in slug_lower:
            continue

        result.append(url)
    return result
