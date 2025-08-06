import os
import time
import pprint
from decimal import Decimal, InvalidOperation
from seleniumbase import SB
from dotenv import load_dotenv
from db_handler import DatabaseHandler

load_dotenv()
print("--- Starting Idealo Scraper ---")

# --- Configuration ---
SCRAPE_URL = os.getenv("SCRAPE_URL_IDEALO", "")
MAX_PAGES_TO_SCRAPE = int(os.getenv("MAX_PAGES_TO_SCRAPE", 2))
IS_HEADLESS = os.getenv("IS_HEADLESS_IDEALO", "False").lower() == "true"


def handle_cookie_consent(sb):
    print("Looking for cookie consent button...")
    try:
        # pierce the Shadow DOM
        accept_button_selector = "aside#usercentrics-cmp-ui::shadow button#accept"
        
        sb.click(accept_button_selector, timeout=10)
        print("Clicked the 'Accept' button.")
        
        sb.wait_for_element_not_visible('aside#usercentrics-cmp-ui', timeout=5)
        print("Cookie banner is gone.")
        return True

    except Exception as e:
        print(f"Could not click the cookie button. Error: {e}")
        sb.save_screenshot("cookie_error.png")
        sb.sleep(10)
        return False

def scrape_products(all_scraped_products, sb):
    for page_num in range(1, MAX_PAGES_TO_SCRAPE + 1):
        print(f"\n--- Scraping Page {page_num} ---")
        
        print("Scrolling slowly to the bottom.")
        time.sleep(2)
        sb.slow_scroll_to('a[aria-label="Nächste Seite"]')
        time.sleep(2)

        results_container_selector = 'div[class*="sr-resultList"]'
        sb.wait_for_element_present(results_container_selector, timeout=10)
        
        soup = sb.get_beautiful_soup()
        product_cards = soup.select('div[class*="sr-resultList__item"]')
        
        print(f"Found {len(product_cards)} product cards on this page.")

        if not product_cards:
            print("No product cards found. Saving a screenshot for debugging.")
            sb.save_screenshot("no_products_found.png")
            break

        for card in product_cards:
            product_data = parse_product_card(card)
            if product_data:
                all_scraped_products.append(product_data)

        # go to next page
        if page_num < MAX_PAGES_TO_SCRAPE:
            try:
                print("Attempting to click 'Next Page'...")
                if sb.is_element_present('a[aria-label="Nächste Seite"]'):
                    sb.click('a[aria-label="Nächste Seite"]')
                    sb.wait_for_element_present(results_container_selector, timeout=10)
                    time.sleep(2)
                else:
                    print("'Next Page' button not found. Assuming last page.")
                    break
            except Exception:
                print("No more pages found. Ending scrape.")
                break

def parse_product_card(card):
    try:
        import json
        import re

        # title
        title_tag = card.select_one('div[class*="sr-productSummary__title"]')
        name = title_tag.get_text(strip=True) if title_tag else 'N/A'

        # link and url
        source_url = 'N/A'
        
        # Method 1
        link_tag = card.select_one('a[class*="sr-resultItemTile__link"]')
        if link_tag and link_tag.get('href'):
            raw_url = link_tag.get('href')
            if raw_url and not raw_url.startswith('https://'):
                source_url = f"https://www.idealo.de{raw_url}"
            else:
                source_url = raw_url
        
        # Method 2
        if 'ipc/prg' in source_url or source_url == 'N/A':
            wishlist_tag = card.select_one('[data-wishlist-heart]')
            if wishlist_tag:
                wishlist_data = json.loads(wishlist_tag['data-wishlist-heart'])
                product_id = wishlist_data.get('id')
                if product_id:
                    source_url = f"https://www.idealo.de/preisvergleich/OffersOfProduct/{product_id}.html"

        # price
        price_tag = card.select_one('div[class*="sr-detailedPriceInfo__price"]')
        price = 'N/A'
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price_match = re.search(r'[\d,.]+', price_text)
            if price_match:
                price_cleaned = price_match.group(0).replace('.', '').replace(',', '.')
                try:
                    price = Decimal(price_cleaned)
                except InvalidOperation:
                    price = 'N/A'
        
        # image url
        image_tag = card.select_one('img[class*="sr-resultItemTile__image"]')
        image_url = image_tag.get('data-src') or image_tag.get('src') if image_tag else 'N/A'
        
        # discount
        discount_tag = card.select_one('span[class*="sr-bargainBadge__savingBadge"]')
        discount = None
        if discount_tag:
            discount_text = discount_tag.get_text(strip=True)
            try:
                discount_value = re.search(r'\d+', discount_text)
                if discount_value:
                    discount = int(discount_value.group(0))
            except (ValueError, TypeError):
                discount = None

        # skip if essential data is missing
        if name == 'N/A' or source_url == 'N/A' or 'ipc/prg' in source_url:
            return None

        return {
            "name": name,
            "price": price,
            "discount": discount,
            "source_url": source_url,
            "image_url": image_url
        }
    except Exception as e:
        print(f"ould not process a card. Error: {e}")
        return None


def scrape_idealo():
    all_scraped_products = []
    print("Launching browser ...")

    with SB(uc=True, headless=IS_HEADLESS) as sb:
        sb.open(SCRAPE_URL)
        time.sleep(2)
        
        handle_cookie_consent(sb)

        scrape_products(all_scraped_products, sb)

    print(f"\n Scraping complete. Found a total of {len(all_scraped_products)} products.")
    return all_scraped_products


if __name__ == "__main__":
    scraped_data = scrape_idealo()

    if scraped_data:
        print("\n--- Storing data in the database ---")
        try:
            with DatabaseHandler() as db:
                db.process_scraped_data(scraped_data)
        except Exception as e:
            print(f"!!! A critical database error occurred: {e}")
    else:
        print("No data was scraped to process.")
        
    print(f"--- Scraper run finished. ---")
