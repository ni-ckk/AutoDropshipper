import os
import time
import re
import pprint
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from seleniumbase import SB
from dotenv import load_dotenv

load_dotenv()

# config
IS_HEADLESS = os.getenv("IS_HEADLESS_EBAY", "true").lower() == "true"
BASE_URL = "https://www.ebay.de/sch/i.html"
MAX_BESTMATCH_ITEMS = int(os.getenv("MAX_BESTMATCH_ITEMS", 10))
MAX_LEASTMATCH_ITEMS = int(os.getenv("MAX_LEASTMATCH_ITEMS", 3))
EBAY_MIN_PRICE = int(os.getenv("EBAY_MIN_PRICE", 50))


def handle_cookie_consent(sb):
    print("Looking for cookie consent button...")
    try:
        sb.click('button#gdpr-banner-accept', timeout=15)
        print("Clicked the eBay cookie accept button.")
    except Exception:
        print("Cookie consent button not found or already accepted.")


def parse_product_item(item_soup):
    try:
        title_selector = 'div.s-item__title > span'
        subtitle_selector = 'div.s-item__subtitle'
        price_selector = 'span.s-item__price'
        url_selector = 'a.s-item__link'
        image_selector = 'div.s-item__image img'
        title_tag = item_soup.select_one(title_selector)
        title = title_tag.get_text(strip=True) if title_tag else None
        subtitle_tag = item_soup.select_one(subtitle_selector)
        subtitle = subtitle_tag.get_text(strip=True, separator=' ') if subtitle_tag else None
        price_tag = item_soup.select_one(price_selector)
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price_match = re.search(r'[\d,.]+', price_text)
        price = None
        if price_match:
            price_cleaned = price_match.group(0).replace('.', '').replace(',', '.')
            try: price = Decimal(price_cleaned)
            except InvalidOperation: price = None
        url_tag = item_soup.select_one(url_selector)
        source_url = url_tag['href'] if url_tag else None
        image_tag = item_soup.select_one(image_selector)
        image_url = image_tag.get('src') or image_tag.get('data-src') if image_tag else None
        if not all([title, price, source_url]): return None
        return {"title": title, "subtitle": subtitle, "price": price, "source_url": source_url, "image_url": image_url}
    except Exception as e:
        print(f"Could not parse an item. Error: {e}")
        return None


def _format_product_list(product_list_raw, is_best_match, source_price):
    formatted_list = []
    for p in product_list_raw:
        formatted_list.append({
            "is_best_match": is_best_match,
            "potential_profit": p['price'] - source_price,
            "Ebay product title": p['title'],
            "Ebay product subtitle": p['subtitle'],
            "Ebay product price": p['price'],
            "Ebay product link": p['source_url'],
            "Ebay product image link": p['image_url']
        })
    return formatted_list


def find_products_on_ebay(product_string, source_price):
    params = {'_nkw': product_string, '_from': 'R40', '_sacat': '0', 'LH_PrefLoc': '6', 'LH_BIN': '1', '_sop': '15'}
    
    print(f"--- Starting eBay scrape for '{product_string}' ---")
    
    with SB(uc=True, headless=IS_HEADLESS) as sb:
        is_filtered_by_min_price = False
        
        for attempt in range(2):
            if is_filtered_by_min_price:
                params['_udlo'] = EBAY_MIN_PRICE
            
            search_url = f"{BASE_URL}?{urlencode(params)}"
            print(f"\n--- Opening URL (Attempt #{attempt+1}): {search_url} ---")
            
            sb.open(search_url)
            time.sleep(2)
            if attempt == 0: handle_cookie_consent(sb)
            time.sleep(1)

            soup = sb.get_beautiful_soup()
            
            has_no_best_matches = bool(soup.select_one("div.srp-save-null-search__title"))

            list_items = soup.select('ul.srp-results > li')
            all_products_raw, divider_index, item_count = [], -1, 0
            
            for item in list_items:
                class_list = item.get('class')
                if class_list and 'srp-river-answer--REWRITE_START' in class_list and "Ergebnisse für weniger Suchbegriffe" in item.get_text():
                    divider_index = item_count
                    break
                if isinstance(class_list, list) and 's-item' in class_list:
                    item_count += 1
            
            if has_no_best_matches:
                print("--- Branch: No best matches found. ---")
                if not is_filtered_by_min_price:
                    print("--- Decision: Re-searching with min price filter. ---")
                    is_filtered_by_min_price = True
                    continue
                else:
                    print("--- Decision: Already filtered. Scraping available items. ---")
                    for item in list_items:
                        class_list = item.get('class')
                        if isinstance(class_list, list) and 's-item' in class_list:
                            product_data = parse_product_item(item)
                            if product_data: all_products_raw.append(product_data)
                    return {
                        "idealo_product_title": product_string, "scraped_at": datetime.now().isoformat(),
                        "best_matches": [],
                        "less_relevant_matches": _format_product_list(all_products_raw[:MAX_LEASTMATCH_ITEMS], False, source_price)
                    }

            best_match_count = divider_index if divider_index != -1 else item_count

            if best_match_count >= MAX_BESTMATCH_ITEMS:
                print(f"--- Branch: Found {best_match_count} best matches (>= limit of {MAX_BESTMATCH_ITEMS}). ---")
                if not is_filtered_by_min_price:
                    print("--- Decision: Re-searching with min price filter. ---")
                    is_filtered_by_min_price = True
                    continue
                else:
                    print("--- Decision: Already filtered. Scraping best matches only. ---")
                    for item in list_items:
                        class_list = item.get('class')
                        if isinstance(class_list, list) and 's-item' in class_list:
                            product_data = parse_product_item(item)
                            if product_data: all_products_raw.append(product_data)
                    return {
                        "idealo_product_title": product_string, "scraped_at": datetime.now().isoformat(),
                        "best_matches": _format_product_list(all_products_raw[:MAX_BESTMATCH_ITEMS], True, source_price),
                        "less_relevant_matches": []
                    }

            print(f"--- Branch: Found {best_match_count} best matches (< limit). Scraping all. ---")
            for item in list_items:
                class_list = item.get('class')
                if isinstance(class_list, list) and 's-item' in class_list:
                    product_data = parse_product_item(item)
                    if product_data: all_products_raw.append(product_data)
            
            best_match_raw = all_products_raw[:divider_index] if divider_index != -1 else all_products_raw
            other_raw = all_products_raw[divider_index:] if divider_index != -1 else []
            
            return {
                "idealo_product_title": product_string, "scraped_at": datetime.now().isoformat(),
                "best_matches": _format_product_list(best_match_raw, True, source_price),
                "less_relevant_matches": _format_product_list(other_raw[:MAX_LEASTMATCH_ITEMS], False, source_price)
            }


if __name__ == "__main__":
    print("--- Running Test Case 1: With Mixed Results ---")
    product_to_find_1 = "Honeywell Net Base Docking Cradle (Anschlußstand) (CT40-NB-UVN-2)"
    test_source_price_1 = Decimal("90.00")
    result_1 = find_products_on_ebay(product_to_find_1, test_source_price_1)
    pprint.pprint(result_1)
    
    print("\n" + "="*50 + "\n")

    print("--- Running Test Case 2: With Tons of Bestmatches ---")
    product_to_find_2 = "Toshiba 24WL3C63DA"
    test_source_price_2 = Decimal("150.00")
    result_2 = find_products_on_ebay(product_to_find_2, test_source_price_2)
    pprint.pprint(result_2)

    print("\n" + "="*50 + "\n")
    
    print("--- Running Test Case 3: No Exact Matches ---")
    product_to_find_3 = "A_VERY_SPECIFIC_PRODUCT_THAT_DOES_NOT_EXIST_XYZ123"
    test_source_price_3 = Decimal("100.00")
    result_3 = find_products_on_ebay(product_to_find_3, test_source_price_3)
    pprint.pprint(result_3)

    print("\n--- eBay scraper run finished. ---")