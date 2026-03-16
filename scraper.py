"""
Apartment scraper for German real estate sites.
Searches ImmoScout24, Immowelt, eBay Kleinanzeigen, WG-Gesucht.
"""

import os
import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class Listing:
    id: str
    title: str
    price: str
    size: str
    rooms: str
    address: str
    url: str
    source: str
    image_url: Optional[str] = None
    description: str = ""
    extras: dict = field(default_factory=dict)

    def to_dict(self):
        return self.__dict__


def _get(url: str, params: dict = None) -> Optional[BeautifulSoup]:
    """Fetch a page with retries and polite delay."""
    time.sleep(random.uniform(1.5, 3.5))
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return None


# ── CONFIG (read from env) ────────────────────────────────────────────────────

def get_config():
    return {
        "city":      os.environ.get("CITY", "Berlin"),
        "min_rooms": float(os.environ.get("MIN_ROOMS", "2")),
        "max_rooms": float(os.environ.get("MAX_ROOMS", "4")),
        "min_size":  int(os.environ.get("MIN_SIZE", "40")),
        "max_size":  int(os.environ.get("MAX_SIZE", "120")),
        "max_price": int(os.environ.get("MAX_PRICE", "1500")),
        "min_price": int(os.environ.get("MIN_PRICE", "0")),
    }


# ── IMMOSCOUT24 ───────────────────────────────────────────────────────────────

def scrape_immoscout(cfg) -> list[Listing]:
    listings = []
    city = cfg["city"].lower().replace(" ", "-")
    base = (
        f"https://www.immobilienscout24.de/Suche/de/{city}/wohnung-mieten"
        f"?numberofrooms={cfg['min_rooms']:.1f}-{cfg['max_rooms']:.1f}"
        f"&livingspace={cfg['min_size']}.0-{cfg['max_size']}.0"
        f"&price={cfg['min_price']}.0-{cfg['max_price']}.0"
        f"&enteredFrom=result_list"
    )
    soup = _get(base)
    if not soup:
        return listings

    cards = soup.select("li[data-id]")
    for card in cards[:15]:
        try:
            lid = card.get("data-id", "")
            title_el = card.select_one('[data-testid="result-list-entry-title"]') or card.select_one(".result-list-entry__brand-title")
            price_el = card.select_one('[data-testid="cardmain-price"]') or card.select_one(".result-list-entry__criteria dt:contains('Kaltmiete') + dd")
            size_el  = card.select_one('[data-testid="cardmain-area"]')
            rooms_el = card.select_one('[data-testid="cardmain-rooms"]')
            addr_el  = card.select_one('[data-testid="result-list-entry-address"]') or card.select_one(".result-list-entry__address")
            link_el  = card.select_one("a[href*='/expose/']")
            img_el   = card.select_one("img[src]")

            url = ("https://www.immobilienscout24.de" + link_el["href"]) if link_el else base

            listings.append(Listing(
                id=f"is24_{lid}",
                title=title_el.get_text(strip=True) if title_el else "—",
                price=price_el.get_text(strip=True) if price_el else "?",
                size=size_el.get_text(strip=True) if size_el else "?",
                rooms=rooms_el.get_text(strip=True) if rooms_el else "?",
                address=addr_el.get_text(strip=True) if addr_el else cfg["city"],
                url=url,
                source="ImmoScout24",
                image_url=img_el["src"] if img_el else None,
            ))
        except Exception as e:
            log.debug(f"ImmoScout parse error: {e}")

    log.info(f"ImmoScout24: {len(listings)} listings")
    return listings


# ── IMMOWELT ──────────────────────────────────────────────────────────────────

def scrape_immowelt(cfg) -> list[Listing]:
    listings = []
    city = cfg["city"].lower()
    base = (
        f"https://www.immowelt.de/liste/{city}/wohnungen/mieten"
        f"?ami={cfg['min_size']}&ama={cfg['max_size']}"
        f"&pri={cfg['min_price']}&pra={cfg['max_price']}"
        f"&rms={int(cfg['min_rooms'])}&rma={int(cfg['max_rooms'])}"
    )
    soup = _get(base)
    if not soup:
        return listings

    cards = soup.select("[data-testid='serp-core-classified-card-testid']") or soup.select(".EstateItem-list")
    for card in cards[:15]:
        try:
            lid_el = card.get("data-estateid") or card.get("id", "")
            title_el = card.select_one("h2") or card.select_one(".EstateItem-title")
            price_el = card.select_one("[data-testid='price']") or card.select_one(".EstateItem-price")
            size_el  = card.select_one("[data-testid='area']")
            rooms_el = card.select_one("[data-testid='rooms']")
            addr_el  = card.select_one("[data-testid='location']") or card.select_one(".EstateItem-address")
            link_el  = card.select_one("a[href*='/expose/']") or card.select_one("a[href]")
            img_el   = card.select_one("img")

            href = link_el["href"] if link_el else ""
            url = href if href.startswith("http") else "https://www.immowelt.de" + href

            listings.append(Listing(
                id=f"iw_{lid_el}",
                title=title_el.get_text(strip=True) if title_el else "—",
                price=price_el.get_text(strip=True) if price_el else "?",
                size=size_el.get_text(strip=True) if size_el else "?",
                rooms=rooms_el.get_text(strip=True) if rooms_el else "?",
                address=addr_el.get_text(strip=True) if addr_el else cfg["city"],
                url=url,
                source="Immowelt",
                image_url=img_el.get("src") if img_el else None,
            ))
        except Exception as e:
            log.debug(f"Immowelt parse error: {e}")

    log.info(f"Immowelt: {len(listings)} listings")
    return listings


# ── EBAY KLEINANZEIGEN ────────────────────────────────────────────────────────

def scrape_ebay(cfg) -> list[Listing]:
    listings = []
    city = cfg["city"].lower()
    base = (
        f"https://www.kleinanzeigen.de/s-wohnung-mieten/{city}"
        f"/preis:{cfg['min_price']}:{cfg['max_price']}/c203"
    )
    soup = _get(base)
    if not soup:
        return listings

    cards = soup.select("article.aditem")
    for card in cards[:15]:
        try:
            lid = card.get("data-adid", "")
            title_el = card.select_one(".ellipsis")
            price_el = card.select_one(".aditem-main--middle--price-shipping--price")
            addr_el  = card.select_one(".aditem-main--top--left")
            desc_el  = card.select_one(".aditem-main--middle--description")
            link_el  = card.select_one("a[href*='/s-anzeige/']")
            img_el   = card.select_one("img[src]")

            href = link_el["href"] if link_el else ""
            url = "https://www.kleinanzeigen.de" + href if href else base

            # Try to extract room/size info from title/description
            text = (title_el.get_text() if title_el else "") + " " + (desc_el.get_text() if desc_el else "")
            rooms_match = re.search(r"(\d[,.]?\d?)\s*[Zz]immer", text)
            size_match  = re.search(r"(\d+)\s*m[²2]", text)

            listings.append(Listing(
                id=f"ebay_{lid}",
                title=title_el.get_text(strip=True) if title_el else "—",
                price=price_el.get_text(strip=True) if price_el else "?",
                size=size_match.group(0) if size_match else "?",
                rooms=rooms_match.group(0) if rooms_match else "?",
                address=addr_el.get_text(strip=True) if addr_el else cfg["city"],
                url=url,
                source="eBay Kleinanzeigen",
                image_url=img_el["src"] if img_el else None,
                description=desc_el.get_text(strip=True)[:200] if desc_el else "",
            ))
        except Exception as e:
            log.debug(f"eBay parse error: {e}")

    log.info(f"eBay Kleinanzeigen: {len(listings)} listings")
    return listings


# ── WG-GESUCHT ────────────────────────────────────────────────────────────────

def scrape_wggesucht(cfg) -> list[Listing]:
    listings = []
    # WG-Gesucht city IDs for major cities
    city_ids = {
        "berlin": 8, "hamburg": 55, "munich": 90, "münchen": 90,
        "cologne": 73, "köln": 73, "frankfurt": 41, "stuttgart": 124,
        "düsseldorf": 30, "leipzig": 77, "dortmund": 25, "bremen": 17,
        "hannover": 56, "nuremberg": 96, "nürnberg": 96,
    }
    city_id = city_ids.get(cfg["city"].lower(), 8)
    base = (
        f"https://www.wg-gesucht.de/wohnungen-in-{cfg['city'].lower()}.{city_id}.2.1.0.html"
        f"?rent_types[]=2&rent_from={cfg['min_price']}&rent_to={cfg['max_price']}"
    )
    soup = _get(base)
    if not soup:
        return listings

    cards = soup.select(".wgg_card") or soup.select("[data-id]")
    for card in cards[:15]:
        try:
            lid = card.get("data-id", card.get("id", ""))
            title_el = card.select_one(".truncate_title") or card.select_one("h3")
            price_el = card.select_one(".col-xs-3 b") or card.select_one(".noprint b")
            size_el  = card.select_one(".col-xs-3:nth-child(2) b")
            rooms_el = card.select_one(".col-xs-3:nth-child(3) b")
            addr_el  = card.select_one(".col-xs-11 span") or card.select_one(".list-details-ad-address")
            link_el  = card.select_one("a[href*='/wohnungen-in-']") or card.select_one("a[href*='.html']")
            img_el   = card.select_one("img[src]")

            href = link_el["href"] if link_el else ""
            url = "https://www.wg-gesucht.de" + href if href and not href.startswith("http") else href or base

            listings.append(Listing(
                id=f"wgg_{lid}",
                title=title_el.get_text(strip=True) if title_el else "—",
                price=price_el.get_text(strip=True) if price_el else "?",
                size=size_el.get_text(strip=True) if size_el else "?",
                rooms=rooms_el.get_text(strip=True) if rooms_el else "?",
                address=addr_el.get_text(strip=True) if addr_el else cfg["city"],
                url=url,
                source="WG-Gesucht",
                image_url=img_el["src"] if img_el else None,
            ))
        except Exception as e:
            log.debug(f"WG-Gesucht parse error: {e}")

    log.info(f"WG-Gesucht: {len(listings)} listings")
    return listings


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def scrape_all() -> list[Listing]:
    cfg = get_config()
    log.info(f"Searching in {cfg['city']} | "
             f"{cfg['min_rooms']}–{cfg['max_rooms']} rooms | "
             f"{cfg['min_size']}–{cfg['max_size']} m² | "
             f"€{cfg['min_price']}–€{cfg['max_price']}/mo")

    all_listings = []
    for fn in [scrape_immoscout, scrape_immowelt, scrape_ebay, scrape_wggesucht]:
        try:
            all_listings.extend(fn(cfg))
        except Exception as e:
            log.error(f"Scraper {fn.__name__} crashed: {e}")

    # Deduplicate by id
    seen = set()
    unique = []
    for l in all_listings:
        if l.id not in seen:
            seen.add(l.id)
            unique.append(l)

    log.info(f"Total unique listings: {len(unique)}")
    return unique
