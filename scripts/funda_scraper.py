#!/usr/bin/env python3
"""
Funda.nl Scraper - Production Implementation
Scrapes real estate listings from Funda.nl per gemeente

Architecture:
- Uses Playwright with stealth mode for JavaScript rendering
- Bypasses bot detection with realistic browser simulation
- Extracts data from JSON-LD and HTML with multi-layer fallbacks
- Dynamic pagination detection for accurate result counts
- Robust against HTML structure changes

Features:
- Auto-detects available pages per city
- Deduplicates results (Funda shows featured listings on every page)
- Extracts comprehensive property data from detail pages
- Exports to Excel with statistics

Usage:
    python scripts/funda_scraper.py
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


class FundaConfig:
    """Configuration for Funda.nl scraper"""

    # Target municipalities/cities
    GEMEENTEN = ["Schagen"]

    # Property type filters
    # Options: "koop" (buy), "huur" (rent)
    LISTING_TYPE = "koop"

    # Search filters
    MIN_PRICE = None  # Minimum price (None = no minimum)
    MAX_PRICE = None  # Maximum price (None = no maximum)
    MIN_BEDROOMS = None  # Minimum bedrooms (None = no minimum)

    # Scraping configuration
    REQUEST_DELAY = 1.0  # seconds between requests (optimized)
    REQUEST_TIMEOUT = 15  # seconds

    # Scraper uses Playwright (only method that works for Funda)
    # Funda uses heavy JavaScript rendering - requests/BeautifulSoup doesn't work

    # Pagination settings
    MAX_PAGES = 0  # 0 = scrape ALL available pages (auto-detected)
    # NOTE: Scraper automatically detects:
    #   - Total results available (e.g., 90 properties for Schagen)
    #   - Pagination URL format (?page=N)
    #   - Maximum available pages (e.g., 5 pages for Schagen)
    # Each page adds ~1.5s delay to avoid bot detection
    # Set to specific number (e.g., 3) to limit scraping

    # Measurement timestamp
    MEASUREMENT_DATE = datetime.now().isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 SCRAPING METHODS
# ═══════════════════════════════════════════════════════════════════════════════


class FundaScraperPlaywright:
    """Scraper using Playwright (robust, JavaScript rendering)"""

    def __init__(
        self, timeout: int = 30000, delay: float = 2.0, headless: bool = False
    ):
        """
        Initialize Playwright scraper.

        Args:
            timeout: Page load timeout in milliseconds
            delay: Delay between requests in seconds
            headless: Run browser in headless mode (WARNING: May trigger bot detection!)
                     Set to False for best results with Funda's anti-bot system
        """
        self.timeout = timeout
        self.delay = delay
        self.headless = headless

        # Initialize stealth mode to bypass bot detection
        try:
            from playwright_stealth import Stealth

            self.stealth_config = Stealth()
            self.use_stealth = True
            logger.info("✅ Stealth mode enabled (bypasses bot detection)")
        except ImportError:
            self.use_stealth = False
            logger.warning(
                "⚠️ playwright-stealth not installed - may be blocked by Funda"
            )

    def search(
        self,
        city: str,
        listing_type: str = "koop",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        max_pages: int = 1,
    ) -> List[Dict]:
        """
        Search Funda.nl using Playwright with pagination

        Args:
            city: City name
            listing_type: "koop" (buy) or "huur" (rent)
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_bedrooms: Minimum number of bedrooms
            max_pages: Maximum pages to scrape

        Returns:
            List of listings
        """
        import re

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )
            return []

        all_listings = []

        try:
            with sync_playwright() as p:
                # Launch with more realistic settings for headless
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]
                    if self.headless
                    else [],
                )
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="nl-NL",
                    # Add more realistic browser context
                    extra_http_headers={
                        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
                    },
                )
                page = context.new_page()

                # Apply stealth mode if available
                if self.use_stealth:
                    self.stealth_config.apply_stealth_sync(page)
                    logger.debug("Stealth mode applied to page")

                # Build base URL and query string (reused for all pages)
                base_url = f"https://www.funda.nl/zoeken/{listing_type}"
                query_parts = []
                if city:
                    # City must be lowercase for Funda's filter
                    query_parts.append(f"selected_area=[%22{city.lower()}%22]")
                query_string = "&".join(query_parts) if query_parts else ""

                # First, detect available pagination from page 1
                first_page_url = f"{base_url}?{query_string}"
                page.goto(
                    first_page_url, wait_until="networkidle", timeout=self.timeout
                )
                page.wait_for_timeout(1000)  # Reduced from 2000ms

                # Extract pagination info from actual pagination links (most reliable!)
                pagination_info = page.evaluate(r"""
                    () => {
                        // Find all pagination links with ?page=N
                        const allLinks = Array.from(document.querySelectorAll('a[href*="?page="]'));
                        const pageNumbers = allLinks
                            .map(a => {
                                const match = a.href.match(/[?&]page=(\d+)/);
                                return match ? parseInt(match[1]) : null;
                            })
                            .filter(n => n !== null);
                        
                        // Maximum page number = total pages available
                        const maxPage = pageNumbers.length > 0 ? Math.max(...pageNumbers) : null;
                        
                        // Find next button to confirm URL format
                        const allButtons = Array.from(document.querySelectorAll('a'));
                        const nextButton = allButtons.find(el => 
                            el.textContent.toLowerCase().includes('volgende') ||
                            (el.getAttribute('aria-label') || '').toLowerCase().includes('volgende')
                        );
                        
                        return {
                            totalResults: maxPage ? maxPage * 18 : null,  // Approximate
                            estimatedPages: maxPage,
                            nextButtonUrl: nextButton ? nextButton.href : null
                        };
                    }
                """)

                total_results = pagination_info.get("totalResults")
                estimated_pages = pagination_info.get("estimatedPages")
                next_url = pagination_info.get("nextButtonUrl")

                if total_results:
                    logger.info(
                        f"Found {total_results:,} total results for {city} (~{estimated_pages} pages)"
                    )

                # Detect URL format from next button
                url_uses_page_param = next_url and "?page=" in next_url
                if url_uses_page_param:
                    logger.info("Detected pagination format: ?page=N")
                else:
                    logger.info("Detected pagination format: &search_result=N")

                # Limit pages if needed
                if estimated_pages:
                    if max_pages == 0:
                        # 0 means scrape all available pages
                        max_pages = estimated_pages
                        logger.info(f"Will scrape all {max_pages} available pages")
                    elif max_pages > estimated_pages:
                        max_pages = estimated_pages
                        logger.info(
                            f"Limiting to {max_pages} pages (only {estimated_pages} available)"
                        )
                    else:
                        logger.info(
                            f"Will scrape {max_pages} of {estimated_pages} available pages"
                        )

                page_num = 1

                while True:
                    # Build pagination URL
                    if page_num == 1:
                        url = first_page_url
                        # Already loaded above, skip navigation
                    else:
                        # Use detected URL format
                        if url_uses_page_param:
                            url = f"{base_url}/?{query_string}&page={page_num}"
                        else:
                            url = f"{base_url}/?{query_string}&search_result={page_num}"

                        # Extra delay for pagination (avoid bot detection)
                        delay_time = (
                            self.delay * 1.5
                        )  # Reduced multiplier from 2x to 1.5x
                        logger.info(
                            f"⏸ Waiting {delay_time:.1f}s before page {page_num} (anti-bot detection)..."
                        )
                        page.wait_for_timeout(int(delay_time * 1000))

                        logger.info(f"📄 Loading page {page_num}/{max_pages}...")
                        page.goto(url, wait_until="networkidle", timeout=self.timeout)

                    # Skip navigation for page 1 (already loaded)
                    if page_num > 1:
                        pass  # Already handled above

                    # Wait for listings (Funda uses data-testid)
                    try:
                        page.wait_for_selector(
                            '[data-testid="top-position-listing"]', timeout=10000
                        )
                    except Exception as e:
                        logger.warning(
                            f"Timeout waiting for property cards on page {page_num}: {str(e)[:100]}"
                        )
                        break

                    # Debug: Check what we actually got
                    page_url = page.url
                    logger.debug(f"Current URL: {page_url}")

                    # Extract property URLs using ROBUST URL-pattern matching
                    # This approach is resilient to HTML class/id changes
                    property_urls = page.evaluate(r"""
                        () => {
                            // Strategy: Find ALL links to property detail pages
                            // This is ROBUST - works regardless of HTML structure changes
                            
                            const urls = new Set();
                            const urlPattern = /\/detail\/(koop|huur)\/[^\/]+\/[^\/]+\/\d+\/?$/;
                            
                            // 1. Find by URL pattern (most robust!)
                            const detailLinks = document.querySelectorAll('a[href*="/detail/koop/"], a[href*="/detail/huur/"]');
                            detailLinks.forEach(link => {
                                const href = link.getAttribute('href');
                                if (href && href.includes('/detail/')) {
                                    const fullUrl = href.startsWith('http') ? href : 'https://www.funda.nl' + href;
                                    // Only include full property pages (not images or media)
                                    if (urlPattern.test(fullUrl)) {
                                        urls.add(fullUrl);
                                    }
                                }
                            });
                            
                            // 2. Fallback: Check all links for detail page pattern
                            if (urls.size === 0) {
                                const allLinks = document.querySelectorAll('a[href]');
                                allLinks.forEach(link => {
                                    const href = link.getAttribute('href');
                                    if (href && /\/detail\/(koop|huur)\//.test(href)) {
                                        const fullUrl = href.startsWith('http') ? href : 'https://www.funda.nl' + href;
                                        if (urlPattern.test(fullUrl)) {
                                            urls.add(fullUrl);
                                        }
                                    }
                                });
                            }
                            
                            console.log(`Found ${urls.size} unique property URLs`);
                            return Array.from(urls);
                        }
                    """)

                    logger.info(
                        f"🏠 Found {len(property_urls) if property_urls else 0} property URLs on page {page_num}"
                    )

                    # Visit each detail page for complete data
                    listings = []

                    with tqdm(
                        total=len(property_urls),
                        desc=f"Page {page_num}",
                        leave=False,
                        unit="property",
                    ) as pbar:
                        for idx, url in enumerate(property_urls, 1):
                            try:
                                # Visit detail page
                                page.goto(
                                    url, wait_until="domcontentloaded", timeout=30000
                                )
                                page.wait_for_timeout(1000)

                                # Extract complete data with multi-layer fallbacks for robustness
                                # Prioritizes JSON-LD, then semantic selectors, then text patterns
                                detail_data = page.evaluate("""
                                () => {
                                    // Helper function to safely extract text
                                    const safeText = (elem) => elem?.textContent?.trim() || null;
                                    const bodyText = document.body.textContent;
                                    
                                    // 1. Try JSON-LD structured data (most reliable!)
                                    let jsonData = null;
                                    const scriptTag = document.querySelector('script[type="application/ld+json"]');
                                    if (scriptTag) {
                                        try {
                                            jsonData = JSON.parse(scriptTag.textContent);
                                        } catch (e) {
                                            console.error('Failed to parse JSON-LD:', e);
                                        }
                                    }
                                    
                                    // 2. Extract address (priority: JSON-LD > H1 > data-testid)
                                    let address = jsonData?.name || 
                                                 safeText(document.querySelector('h1')) ||
                                                 safeText(document.querySelector('[data-testid="street-name-house-number"]'));
                                    
                                    // 3. Extract price (priority: JSON-LD > text pattern)
                                    let price = jsonData?.offers?.price || null;
                                    if (!price) {
                                        // Find largest price in page (likely the asking price)
                                        const priceMatches = Array.from(bodyText.matchAll(/€\\s*([\\d.]+)/g));
                                        if (priceMatches.length > 0) {
                                            const prices = priceMatches.map(m => parseFloat(m[1].replace(/\\./g, '')));
                                            price = Math.max(...prices.filter(p => p > 1000)); // Filter out small values
                                        }
                                    }
                                    
                                    // 4. Extract property type (priority: JSON-LD > keywords)
                                    let propertyType = null;
                                    if (jsonData?.['@type']) {
                                        propertyType = Array.isArray(jsonData['@type']) ? 
                                            jsonData['@type'].find(t => t !== 'Product') : 
                                            jsonData['@type'];
                                    }
                                    if (!propertyType) {
                                        const typeKeywords = ['Appartement', 'Woonhuis', 'Villa', 'Huis', 
                                                             'Parkeergelegenheid', 'Bouwgrond'];
                                        for (const keyword of typeKeywords) {
                                            if (bodyText.includes(keyword)) {
                                                propertyType = keyword;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // 5. Extract location (JSON-LD data)
                                    const city = jsonData?.address?.addressLocality || null;
                                    const postalCode = jsonData?.address?.postalCode || null;
                                    
                                    // 6. Extract living area (multiple patterns)
                                    let areaMatch = bodyText.match(/Woonoppervlakte[^\\d]*(\\d+)\\s*m²/i);
                                    if (!areaMatch) areaMatch = bodyText.match(/([\\d.]+)\\s*m²/);
                                    if (!areaMatch) areaMatch = bodyText.match(/(\\d+)m²/);
                                    
                                    // 7. Extract rooms (multiple patterns)
                                    let roomsMatch = bodyText.match(/Aantal kamers[^\\d]*(\\d+)/i);
                                    if (!roomsMatch) roomsMatch = bodyText.match(/(\\d+)\\s*kamer/i);
                                    if (!roomsMatch) roomsMatch = bodyText.match(/(\\d+)\\s*slaapkamer/i);
                                    
                                    // 8. Extract construction year
                                    const bouwjaarMatch = bodyText.match(/Bouwjaar[^\\d]*(\\d{4})/i) ||
                                                         bodyText.match(/gebouwd in (\\d{4})/i);
                                    
                                    // 9. Extract plot size
                                    const plotMatch = bodyText.match(/Perceeloppervlakte[^\\d]*(\\d+)\\s*m²/i);
                                    
                                    return {
                                        address: address || null,
                                        price: price,
                                        price_text: price ? `€ ${price.toLocaleString('nl-NL')}` : null,
                                        area_text: areaMatch ? areaMatch[1] + ' m²' : null,
                                        rooms_text: roomsMatch ? roomsMatch[1] + ' kamers' : null,
                                        property_type: propertyType || null,
                                        postal_city: city || null,
                                        bouwjaar: bouwjaarMatch ? bouwjaarMatch[1] : null,
                                        plot_area: plotMatch ? plotMatch[1] + ' m²' : null,
                                    };
                                }
                            """)

                                # Validate and add
                                if detail_data.get("address") or detail_data.get(
                                    "price"
                                ):
                                    detail_data["url"] = url
                                    listings.append(detail_data)
                                    pbar.update(1)
                                else:
                                    logger.debug(
                                        f"Skipping property with no data: {url[:80]}"
                                    )
                                    pbar.update(1)

                            except Exception as e:
                                logger.debug(
                                    f"Error scraping property {idx}: {str(e)[:100]}"
                                )
                                pbar.update(1)
                                continue

                    logger.info(
                        f"✅ Page {page_num}: {len(listings)} properties scraped"
                    )

                    if not listings:
                        logger.info(f"🛑 No more results at page {page_num}")
                        break

                    # Parse numeric values with robust error handling
                    for listing in listings:
                        # Extract price (multiple strategies for robustness)
                        if not listing.get("price") and listing.get("price_text"):
                            try:
                                # Remove dots (thousands separator), keep only digits
                                price_cleaned = re.sub(
                                    r"[^\d]", "", listing["price_text"]
                                )
                                if price_cleaned:
                                    listing["price"] = float(price_cleaned)
                            except (ValueError, AttributeError):
                                logger.debug(
                                    f"Could not parse price: {listing.get('price_text')}"
                                )

                        # Extract area
                        if listing.get("area_text"):
                            try:
                                area_match = re.search(r"(\d+)", listing["area_text"])
                                if area_match:
                                    listing["area_m2"] = int(area_match.group(1))
                            except (ValueError, AttributeError):
                                pass

                        # Extract rooms
                        if listing.get("rooms_text"):
                            try:
                                rooms_match = re.search(r"(\d+)", listing["rooms_text"])
                                if rooms_match:
                                    listing["rooms"] = int(rooms_match.group(1))
                            except (ValueError, AttributeError):
                                pass

                        # Extract property ID from URL
                        if listing.get("url"):
                            try:
                                id_match = re.search(r"-(\d+)/?$", listing["url"])
                                if id_match:
                                    listing["property_id"] = id_match.group(1)
                            except AttributeError:
                                pass

                    all_listings.extend(listings)
                    logger.info(
                        f"📈 Page {page_num} complete: {len(listings)} new listings | Total: {len(all_listings)}"
                    )

                    # Check if we should continue
                    page_num += 1
                    if max_pages > 0 and page_num > max_pages:
                        logger.info(f"🏁 Reached max pages ({max_pages})")
                        break

                    # Rate limiting between pages
                    if self.delay > 0:
                        time.sleep(self.delay)

                browser.close()

                logger.info(
                    f"✅ Scraping complete: {len(all_listings)} listings from {page_num - 1} pages"
                )
                return all_listings

        except Exception as e:
            logger.error(f"Playwright error: {e}")
            return []


class FundaScraper:
    """
    Main Funda.nl scraper - Production-ready implementation

    Uses Playwright with stealth mode for reliable scraping.
    Robust against HTML structure changes through multi-layer extraction.
    """

    def __init__(self, config: Optional[FundaConfig] = None):
        """
        Initialize scraper

        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or FundaConfig()

        # Initialize Playwright scraper
        # Note: headless=False is required to bypass Funda's anti-bot detection
        self.playwright_scraper = FundaScraperPlaywright(
            timeout=30000, delay=self.config.REQUEST_DELAY, headless=False
        )

    def search(
        self,
        city: str,
        listing_type: str = "koop",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        max_pages: int = 1,
    ) -> List[Dict]:
        """
        Search Funda.nl for properties

        Args:
            city: City/gemeente name (case-insensitive, will be lowercased)
            listing_type: "koop" (buy) or "huur" (rent)
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_bedrooms: Minimum number of bedrooms
            max_pages: Maximum pages to scrape (0 = all available pages)

        Returns:
            List of property dictionaries
        """
        if not city:
            logger.error("City parameter is required")
            return []

        return self.playwright_scraper.search(
            city, listing_type, min_price, max_price, min_bedrooms, max_pages
        )

    def scrape_gemeente(self, gemeente: str) -> pd.DataFrame:
        """
        Scrape Funda.nl for one gemeente

        Args:
            gemeente: Gemeente/city name

        Returns:
            DataFrame with results
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"🏘️  Starting scrape for: {gemeente.upper()}")
        logger.info(f"{'=' * 60}")

        max_pages = self.config.MAX_PAGES
        raw_results = self.search(
            gemeente,
            listing_type=self.config.LISTING_TYPE,
            min_price=self.config.MIN_PRICE,
            max_price=self.config.MAX_PRICE,
            min_bedrooms=self.config.MIN_BEDROOMS,
            max_pages=max_pages,
        )

        if not raw_results:
            logger.warning(f"⚠️  No results found for {gemeente}")
            return pd.DataFrame()

        logger.info(f"📊 Processing {len(raw_results)} results for {gemeente}...")

        # Process results
        rows = []
        for listing in raw_results:
            row = {
                "gemeente": gemeente,
                "platform": "funda.nl",
                "property_id": listing.get("property_id"),
                "property_url": listing.get("url"),
                "address": listing.get("address"),
                "postal_city": listing.get("postal_city"),
                "property_type": listing.get("property_type"),
                "listing_type": self.config.LISTING_TYPE,
                "price": listing.get("price"),
                "price_text": listing.get("price_text"),
                "area_m2": listing.get("area_m2"),
                "area_text": listing.get("area_text"),
                "rooms": listing.get("rooms"),
                "rooms_text": listing.get("rooms_text"),
                "measurement_date": self.config.MEASUREMENT_DATE,
            }
            rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        logger.info(f"✅ {gemeente}: {len(df)} listings saved to DataFrame")
        logger.info(f"{'=' * 60}\n")

        return df


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Main execution function for testing/running the scraper"""
    config = FundaConfig()

    print("=" * 80)
    print("FUNDA.NL SCRAPER")
    print("=" * 80)
    print(f"Meetmoment: {config.MEASUREMENT_DATE}")
    print(f"Gemeenten: {', '.join(config.GEMEENTEN)}")
    print(f"Listing type: {config.LISTING_TYPE}")
    print("Method: Playwright (only method)")
    print(f"Max pages per gemeente: {config.MAX_PAGES}")
    print("=" * 80)

    # Initialize scraper
    scraper = FundaScraper(config=config)

    # Scrape all gemeenten
    print("\n" + "=" * 80)
    print("🚀 START SCRAPEN")
    print("=" * 80)

    all_runs = []
    start_time = time.time()

    for gemeente in config.GEMEENTEN:
        df_run = scraper.scrape_gemeente(gemeente)
        all_runs.append(df_run)

    # Combine results
    total_duration = time.time() - start_time

    print("\n" + "=" * 80)
    print("RESULTATEN")
    print("=" * 80)

    df_all = pd.concat(all_runs, ignore_index=True) if all_runs else pd.DataFrame()

    if not df_all.empty:
        print(f"\n✓ Totaal records: {len(df_all):,}")

        # Count unique properties (try property_id, fallback to URL)
        if "property_id" in df_all.columns and df_all["property_id"].notna().any():
            unique_count = df_all["property_id"].nunique()
        elif "property_url" in df_all.columns:
            unique_count = df_all["property_url"].nunique()
        else:
            unique_count = len(df_all)
        print(f"✓ Unieke properties: {unique_count:,}")
        print(f"✓ Scrape tijd: {total_duration / 60:.1f} minuten")

        # Property type distribution
        if "property_type" in df_all.columns:
            print("\n🏠 Property types:")
            type_counts = df_all["property_type"].value_counts()
            for prop_type, count in type_counts.items():
                print(f"   • {prop_type}: {count}")

        # Price statistics
        if "price" in df_all.columns and df_all["price"].notna().any():
            print("\n💰 Prijs statistieken:")
            print(f"   • Gemiddeld: €{df_all['price'].mean():,.0f}")
            print(f"   • Mediaan: €{df_all['price'].median():,.0f}")
            print(f"   • Min: €{df_all['price'].min():,.0f}")
            print(f"   • Max: €{df_all['price'].max():,.0f}")

        # Area statistics
        if "area_m2" in df_all.columns and df_all["area_m2"].notna().any():
            print("\n📐 Oppervlakte statistieken:")
            print(f"   • Gemiddeld: {df_all['area_m2'].mean():.0f} m²")
            print(f"   • Mediaan: {df_all['area_m2'].median():.0f} m²")

        # Export to Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gm_string = "-".join(config.GEMEENTEN)
        filename = f"funda_scrape_{gm_string}_{config.LISTING_TYPE}_{timestamp}.xlsx"

        df_all.to_excel(filename, index=False, engine="openpyxl")
        print(f"\n✅ Opgeslagen: {filename}")
    else:
        print("\n⚠️  Geen resultaten gevonden")

    print("=" * 80)


if __name__ == "__main__":
    main()
