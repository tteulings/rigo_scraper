#!/usr/bin/env python3
"""
Booking.com Scraper - Professional Implementation
Scraped Booking.com accommodations per gemeente met multiple methods

Architecture:
- Primary: requests + BeautifulSoup (fast, simple)
- Fallback: Playwright (robust, bypasses anti-bot)
- Spatial filtering with GeoPackage
- Unified data format compatible with Airbnb scraper
"""

import time
import logging
from datetime import date, timedelta, datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
import geopandas as gpd

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


class BookingConfig:
    """Configuration for Booking.com scraper"""

    # Target municipalities
    GEMEENTEN = ["Amsterdam"]

    # Period configuration
    PERIOD_START = "2025-12-01"
    PERIOD_END = "2025-12-05"
    MEASUREMENT_INTERVAL = 1  # days

    # Search variations
    NIGHTS_VARIATIONS = [1, 3, 7]
    GUESTS_VARIATIONS = [1, 2, 4]  # Solo, couple, small group

    # API/Scraping configuration
    NUM_REPEAT_CALLS = 1  # Multiple calls per search for better coverage
    REQUEST_DELAY = 2.0  # seconds between requests
    REQUEST_TIMEOUT = 15  # seconds

    # Files
    GPKG_PATH = "assets/BestuurlijkeGebieden_2025.gpkg"

    # Method selection
    # Options: 'requests', 'playwright', 'both' (tries requests first, falls back to playwright)
    SCRAPE_METHOD = "playwright"  # Changed to playwright for reliability
    
    # Pagination settings
    MAX_PAGES = 10  # Maximum pages to scrape per search (0 = all pages, be careful!)
    # Note: Booking.com has ~25-30 listings per page
    # Amsterdam ~1000 hotels = ~40 pages
    
    # Measurement timestamp
    MEASUREMENT_DATE = datetime.now().isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 SCRAPING METHODS
# ═══════════════════════════════════════════════════════════════════════════════


class BookingScraperRequests:
    """Scraper using requests + BeautifulSoup (fast, lightweight)"""

    def __init__(self, timeout: int = 15, delay: float = 2.0):
        self.timeout = timeout
        self.delay = delay

    def search(
        self, city: str, checkin: str, checkout: str, adults: int, max_pages: int = 1
    ) -> List[Dict]:
        """
        Search Booking.com using requests + BeautifulSoup with pagination

        Args:
            city: City name
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of guests
            max_pages: Maximum pages to scrape (0 = all pages)

        Returns:
            List of listings
        """
        import requests
        from bs4 import BeautifulSoup

        all_listings = []
        page = 0

        while True:
            # Booking.com uses offset parameter for pagination
            offset = page * 25  # ~25 listings per page

            url = (
                f"https://www.booking.com/searchresults.html"
                f"?ss={city}"
                f"&checkin={checkin}"
                f"&checkout={checkout}"
                f"&group_adults={adults}"
                f"&no_rooms=1"
                f"&offset={offset}"
            )

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }

            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)

                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} for {city} page {page + 1}")
                    break

                soup = BeautifulSoup(response.content, "html.parser")

                # Find hotel cards
                hotel_cards = soup.find_all("div", {"data-testid": "property-card"})

                if not hotel_cards:
                    # Fallback: try alternative selectors
                    hotel_cards = soup.find_all(
                        "div", class_=lambda x: x and "property-card" in str(x).lower()
                    )

                if not hotel_cards:
                    # No more results
                    logger.info(f"requests+bs4: No more results at page {page + 1}")
                    break

                page_listings = []
                for card in hotel_cards:
                    listing = self._parse_card(card)
                    if listing:
                        page_listings.append(listing)

                all_listings.extend(page_listings)
                logger.info(
                    f"requests+bs4: Page {page + 1} - Found {len(page_listings)} listings ({len(all_listings)} total)"
                )

                # Check if we should continue
                page += 1
                if max_pages > 0 and page >= max_pages:
                    logger.info(f"requests+bs4: Reached max pages ({max_pages})")
                    break

                # Rate limiting between pages
                if self.delay > 0:
                    time.sleep(self.delay)

            except Exception as e:
                logger.error(f"requests+bs4 error for {city} page {page + 1}: {e}")
                break

        logger.info(
            f"requests+bs4: Total {len(all_listings)} listings from {page} pages for {city}"
        )
        return all_listings

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse a hotel card"""
        try:
            listing = {}

            # Title
            title_elem = card.find("div", {"data-testid": "title"})
            if title_elem:
                listing["title"] = title_elem.get_text(strip=True)
            else:
                # Try alternative selector
                title_elem = card.find(
                    ["h3", "h2"], class_=lambda x: x and "title" in str(x).lower()
                )
                if title_elem:
                    listing["title"] = title_elem.get_text(strip=True)

            # Price
            price_elem = card.find(
                "span", {"data-testid": "price-and-discounted-price"}
            )
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                listing["price_text"] = price_text
                # Extract numeric value
                import re

                price_match = re.search(r"€\s*(\d+)", price_text)
                if price_match:
                    listing["price"] = float(price_match.group(1))

            # Rating
            rating_elem = card.find("div", {"data-testid": "review-score"})
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                listing["rating_text"] = rating_text
                # Extract numeric value
                import re

                rating_match = re.search(r"(\d+[,\.]\d+)", rating_text)
                if rating_match:
                    rating_str = rating_match.group(1).replace(",", ".")
                    listing["rating"] = float(rating_str)

            # URL
            link_elem = card.find("a", href=True)
            if link_elem:
                href = link_elem["href"]
                if href.startswith("http"):
                    listing["url"] = href
                else:
                    listing["url"] = f"https://www.booking.com{href}"

            # Only return if we have at least a title
            if "title" in listing:
                return listing

            return None

        except Exception as e:
            logger.debug(f"Error parsing card: {e}")
            return None


class BookingScraperPlaywright:
    """Scraper using Playwright (robust, JavaScript rendering)"""

    def __init__(self, timeout: int = 30000, delay: float = 2.0, headless: bool = True):
        self.timeout = timeout
        self.delay = delay
        self.headless = headless

    def search(
        self, city: str, checkin: str, checkout: str, adults: int, max_pages: int = 1
    ) -> List[Dict]:
        """
        Search Booking.com using Playwright with pagination

        Args:
            city: City name
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of guests
            max_pages: Maximum pages to scrape (0 = all pages)

        Returns:
            List of listings
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error(
                "Playwright not installed. Install with: pip install playwright"
            )
            return []

        all_listings = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="nl-NL",
                )
                page = context.new_page()

                page_num = 0

                while True:
                    offset = page_num * 25

                    url = (
                        f"https://www.booking.com/searchresults.html"
                        f"?ss={city}"
                        f"&checkin={checkin}"
                        f"&checkout={checkout}"
                        f"&group_adults={adults}"
                        f"&no_rooms=1"
                        f"&offset={offset}"
                    )

                    # Navigate
                    page.goto(url, wait_until="networkidle", timeout=self.timeout)

                    # Wait for listings
                    try:
                        page.wait_for_selector(
                            '[data-testid="property-card"]', timeout=10000
                        )
                    except:
                        logger.warning(
                            f"Timeout waiting for property cards in {city} page {page_num + 1}"
                        )
                        break

                    # Extract data using JavaScript
                    listings = page.evaluate("""
                        () => {
                            const cards = document.querySelectorAll('[data-testid="property-card"]');
                            return Array.from(cards).map(card => {
                                const title = card.querySelector('[data-testid="title"]');
                                const price = card.querySelector('[data-testid="price-and-discounted-price"]');
                                const rating = card.querySelector('[data-testid="review-score"]');
                                const link = card.querySelector('a[href]');
                                
                                return {
                                    title: title ? title.textContent.trim() : null,
                                    price_text: price ? price.textContent.trim() : null,
                                    rating_text: rating ? rating.textContent.trim() : null,
                                    url: link ? link.href : null,
                                };
                            }).filter(item => item.title !== null);
                        }
                    """)

                    if not listings:
                        logger.info(f"Playwright: No more results at page {page_num + 1}")
                        break

                    # Parse numeric values
                    for listing in listings:
                        if listing.get("price_text"):
                            import re

                            price_match = re.search(r"€\s*(\d+)", listing["price_text"])
                            if price_match:
                                listing["price"] = float(price_match.group(1))

                        if listing.get("rating_text"):
                            import re

                            rating_match = re.search(
                                r"(\d+[,\.]\d+)", listing["rating_text"]
                            )
                            if rating_match:
                                rating_str = rating_match.group(1).replace(",", ".")
                                listing["rating"] = float(rating_str)

                    all_listings.extend(listings)
                    logger.info(
                        f"Playwright: Page {page_num + 1} - Found {len(listings)} listings ({len(all_listings)} total)"
                    )

                    # Check if we should continue
                    page_num += 1
                    if max_pages > 0 and page_num >= max_pages:
                        logger.info(f"Playwright: Reached max pages ({max_pages})")
                        break

                    # Rate limiting between pages
                    if self.delay > 0:
                        time.sleep(self.delay)

                browser.close()

                logger.info(
                    f"Playwright: Total {len(all_listings)} listings from {page_num} pages for {city}"
                )
                return all_listings

        except Exception as e:
            logger.error(f"Playwright error for {city}: {e}")
            return []


class BookingScraper:
    """
    Main Booking.com scraper with multiple methods and fallback logic
    """

    def __init__(self, method: str = "both", config: BookingConfig = None):
        """
        Initialize scraper

        Args:
            method: 'requests', 'playwright', or 'both'
            config: Configuration object
        """
        self.method = method
        self.config = config or BookingConfig()

        # Initialize scrapers
        self.requests_scraper = BookingScraperRequests(
            timeout=self.config.REQUEST_TIMEOUT, delay=self.config.REQUEST_DELAY
        )
        self.playwright_scraper = BookingScraperPlaywright(
            delay=self.config.REQUEST_DELAY
        )

    def search(
        self, city: str, checkin: str, checkout: str, adults: int, max_pages: int = 1
    ) -> List[Dict]:
        """
        Search Booking.com with automatic method selection/fallback

        Args:
            city: City name
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of guests
            max_pages: Maximum pages to scrape (0 = all pages)

        Returns:
            List of listings
        """
        if self.method == "requests":
            return self.requests_scraper.search(
                city, checkin, checkout, adults, max_pages
            )

        elif self.method == "playwright":
            return self.playwright_scraper.search(
                city, checkin, checkout, adults, max_pages
            )

        elif self.method == "both":
            # Try requests first (faster)
            results = self.requests_scraper.search(
                city, checkin, checkout, adults, max_pages
            )

            # Fallback to Playwright if no results
            if not results:
                logger.info(f"No results with requests, trying Playwright for {city}")
                results = self.playwright_scraper.search(
                    city, checkin, checkout, adults, max_pages
                )

            return results

        else:
            raise ValueError(f"Invalid method: {self.method}")

    def scrape_gemeente(
        self,
        gemeente: str,
        checkin: str,
        checkout: str,
        nights: int,
        guests: int,
        scan_id: int,
    ) -> pd.DataFrame:
        """
        Scrape Booking.com for one gemeente

        Args:
            gemeente: Gemeente name
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            nights: Number of nights
            guests: Number of guests
            scan_id: Unique scan ID

        Returns:
            DataFrame with results
        """
        logger.info(f"Scraping {gemeente}: {checkin}→{checkout} ({nights}n, {guests}g)")

        # Load gemeente boundaries
        try:
            gdf_all = (
                gpd.read_file(self.config.GPKG_PATH, layer="gemeentegebied")
                .set_crs("EPSG:28992")
                .to_crs("EPSG:4326")
            )
            sel = gdf_all[gdf_all["naam"] == gemeente]

            if sel.empty:
                logger.error(f"No boundary found for gemeente: {gemeente}")
                return pd.DataFrame()

            minx, miny, maxx, maxy = sel.total_bounds
            center_lat = (miny + maxy) / 2
            center_lon = (minx + maxx) / 2

            logger.debug(f"{gemeente} center: {center_lat:.4f}, {center_lon:.4f}")

        except Exception as e:
            logger.error(f"Error loading gemeente boundaries: {e}")
            return pd.DataFrame()

        # Search Booking.com with pagination
        # Note: Booking.com doesn't support bbox search well, so we search by gemeente name
        max_pages = self.config.MAX_PAGES if hasattr(self.config, "MAX_PAGES") else 1
        raw_results = self.search(gemeente, checkin, checkout, guests, max_pages=max_pages)

        if not raw_results:
            logger.warning(f"No results for {gemeente}")
            return pd.DataFrame()

        # Process results
        rows = []
        for listing in raw_results:
            row = {
                "gemeente": gemeente,
                "platform": "booking.com",
                "listing_id": None,  # Booking.com doesn't expose IDs easily
                "listing_url": listing.get("url"),
                "listing_title": listing.get("title"),
                "property_type": "accommodation",  # Generic, would need detail page scraping
                "price": listing.get("price"),
                "rating": listing.get("rating"),
                "scan_checkin": checkin,
                "scan_checkout": checkout,
                "scan_nights": nights,
                "scan_guests": guests,
                "scan_id": scan_id,
                "measurement_date": self.config.MEASUREMENT_DATE,
            }
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        logger.info(f"✓ {gemeente}: {len(df)} listings")

        return df


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════


def generate_scan_combinations(
    period_start: str,
    period_end: str,
    nights_list: List[int],
    guests_list: List[int],
    measurement_interval: int,
) -> Tuple[List[Tuple], List[int]]:
    """Generate scan combinations"""
    start_date = date.fromisoformat(period_start)
    end_date = date.fromisoformat(period_end)
    max_nights = (end_date - start_date).days

    valid_nights = [n for n in nights_list if n <= max_nights]
    if not valid_nights:
        valid_nights = [1]

    combinations = []
    scan_id = 0

    current_date = start_date
    while current_date <= end_date:
        for nights in valid_nights:
            check_out = current_date + timedelta(days=nights)
            if check_out <= end_date + timedelta(days=1):
                for guests in guests_list:
                    scan_id += 1
                    combinations.append(
                        (
                            current_date.isoformat(),
                            check_out.isoformat(),
                            nights,
                            guests,
                            scan_id,
                        )
                    )
        current_date += timedelta(days=measurement_interval)

    return combinations, valid_nights


def main():
    """Main execution function"""
    config = BookingConfig()

    print("=" * 80)
    print("🏨 BOOKING.COM SCRAPER")
    print("=" * 80)
    print(f"Meetmoment: {config.MEASUREMENT_DATE}")
    print(f"Periode: {config.PERIOD_START} → {config.PERIOD_END}")
    print(f"Gemeenten: {', '.join(config.GEMEENTEN)}")
    print(f"Methode: {config.SCRAPE_METHOD}")
    print("=" * 80)

    # Generate scan combinations
    scan_combinations, valid_nights = generate_scan_combinations(
        config.PERIOD_START,
        config.PERIOD_END,
        config.NIGHTS_VARIATIONS,
        config.GUESTS_VARIATIONS,
        config.MEASUREMENT_INTERVAL,
    )

    total_scans = len(scan_combinations) * len(config.GEMEENTEN)

    print(f"\n📊 Totaal Scan Combinaties: {len(scan_combinations)}")
    print(f"🛏️  Nachten Variaties: {valid_nights}")
    print(f"👥 Gasten Variaties: {config.GUESTS_VARIATIONS}")
    print(f"📍 Totaal scans: {total_scans}")

    # Initialize scraper
    scraper = BookingScraper(method=config.SCRAPE_METHOD, config=config)

    # Scrape all combinations
    print("\n" + "=" * 80)
    print("🚀 START SCRAPEN")
    print("=" * 80)

    all_runs = []
    start_time = time.time()
    current_scan = 0

    for ci, co, nights, guests, scan_id in scan_combinations:
        for gemeente in config.GEMEENTEN:
            current_scan += 1

            # Progress
            progress_pct = (current_scan / total_scans) * 100
            print(f"\n[{current_scan:3d}/{total_scans} {progress_pct:5.1f}%] ", end="")

            df_run = scraper.scrape_gemeente(gemeente, ci, co, nights, guests, scan_id)
            all_runs.append(df_run)

    # Combine results
    total_duration = time.time() - start_time

    print("\n\n" + "=" * 80)
    print("📊 RESULTATEN")
    print("=" * 80)

    df_all = pd.concat(all_runs, ignore_index=True) if all_runs else pd.DataFrame()

    if not df_all.empty:
        print(f"\n✓ Totaal records: {len(df_all):,}")
        print(f"✓ Unieke accommodaties: {df_all['listing_title'].nunique():,}")
        print(f"✓ Scrape tijd: {total_duration / 60:.1f} minuten")
        print(f"✓ Gemiddelde prijs: €{df_all['price'].mean():.2f}")

        # Export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gm_string = "-".join(config.GEMEENTEN)
        filename = f"booking_scrape_{gm_string}_{timestamp}.xlsx"

        df_all.to_excel(filename, index=False)
        print(f"\n✅ Opgeslagen: {filename}")
    else:
        print("\n⚠️  Geen resultaten gevonden")

    print("=" * 80)


if __name__ == "__main__":
    main()
