#!/usr/bin/env python3
"""
Main entry point for AutoDropshipper scraper services.

This module provides a unified CLI interface for running both Idealo and eBay scrapers
in a single container environment. Scrapers run sequentially, not in parallel.
"""

import argparse
import sys
from decimal import Decimal
from typing import List, Optional


from src.core.models.ebay_listing import EbayListing
from src.core.models.idealo_product import IdealoProduct
from src.core.models.product_comparison import ProductComparison
from src.core.utils.profitability_calculator import ProfitabilityCalculator
from src.database.repositories.ebay_listing_repository import EbayListingRepository
from src.database.repositories.idealo_product_repository import IdealoProductRepository
from src.scrapers.ebay.ebay_scraper import EbayScraper
from src.scrapers.idealo.idealo_scraper import IdealoScraper
from src.shared.logging.log_setup import get_logger, setup_logging

# setup logging
import os
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_level=log_level)
logger = get_logger(__name__)


def run_idealo_scraper() -> List[IdealoProduct]:
    """
    Run Idealo scraper and return products.
    
    Uses the URL from SCRAPE_URL_IDEALO environment variable which should
    already contain all filters and parameters. Scrapes number of pages
    based on MAX_PAGES_TO_SCRAPE from config.
        
    Returns:
        List of scraped Idealo products
    """
    logger.info("starting_idealo_scraper")
    
    try:
        scraper = IdealoScraper()
        products = scraper.scrape_products()
            
        logger.info("idealo_scraping_completed", products_found=len(products))
        return products
        
    except Exception as e:
        logger.error("idealo_scraping_failed", error=str(e), exc_info=True)
        print(f"ERROR: Idealo scraping failed: {e}")
        return []


def run_ebay_scraper(search_query: str, max_results: int = 20) -> List[EbayListing]:
    """
    Run eBay scraper and return listings.
    
    Args:
        search_query: Product search query  
        max_results: Maximum number of listings to scrape
        
    Returns:
        List of scraped eBay listings
    """
    logger.info("starting_ebay_scraper", query=search_query, max_results=max_results)
    
    try:
        with EbayScraper() as scraper:
            listings = scraper.search_products(search_query, max_results=max_results)
            
        logger.info("ebay_scraping_completed", listings_found=len(listings))
        return listings
        
    except Exception as e:
        logger.error("ebay_scraping_failed", error=str(e), exc_info=True)
        print(f"ERROR: eBay scraping failed: {e}")
        return []


def run_full_production_flow() -> None:
    """
    Run full production flow: Idealo → DB → eBay checks for each product → DB.
    
    This is the main production workflow that:
    1. Scrapes Idealo products
    2. Saves them to database
    3. Automatically checks eBay for new/stale products
    4. Saves eBay listings to database
    """
    print("=" * 60)
    print("  AutoDropshipper Production Flow")
    print("  Idealo → Database → eBay Checks → Database")
    print("=" * 60)
    
    # Step 1: Scrape Idealo products
    print("\nStep 1: Scraping Idealo products...")
    products = run_idealo_scraper()
    
    if not products:
        print("ERROR: No Idealo products found. Stopping.")
        return
    
    print(f"SUCCESS: Found {len(products)} Idealo products")
    
    # Step 2: Save to database and run eBay checks
    print("\nStep 2: Saving to database and checking eBay...")
    save_to_database(products, [])
    
    print("\n" + "=" * 60)
    print("  Production Flow Complete")
    print("=" * 60)


def save_to_database(products: List[IdealoProduct], listings: List[EbayListing]) -> None:
    """
    Save scraped data to database and check eBay for new/stale products.
    
    Args:
        products: Idealo products to save
        listings: eBay listings to save
    """
    from src.database.handlers.connection_handler import ConnectionHandler
    from src.shared.config.app_settings import get_app_config
    
    config = get_app_config()
    
    try:
        with ConnectionHandler() as conn:
            needs_ebay_check = []
            
            # Save Idealo products and track which need eBay checks
            if products:
                idealo_repo = IdealoProductRepository(conn)
                products_data = [
                    {
                        "name": p.name,
                        "price": p.price,
                        "discount": p.discount,
                        "source_url": str(p.source_url),
                        "image_url": str(p.image_url) if p.image_url else None,
                        "category": p.category
                    }
                    for p in products
                ]
                
                # process products and get list of those needing eBay checks
                needs_ebay_check = idealo_repo.process_scraped_products(
                    products_data,
                    ebay_check_threshold_days=config.EBAY_CHECK_THRESHOLD_DAYS
                )
                print(f"SUCCESS: Saved {len(products)} Idealo products to database")
                
                # run eBay checks for new and stale products
                if needs_ebay_check:
                    print(f"\nChecking eBay for {len(needs_ebay_check)} products...")
                    ebay_repo = EbayListingRepository(conn)
                    
                    for idx, product_info in enumerate(needs_ebay_check, 1):
                        print(f"[{idx}/{len(needs_ebay_check)}] Checking eBay for: {product_info['name'][:50]}... ({product_info['type']})")
                        
                        # use existing eBay scraper to search for this product
                        ebay_listings = run_ebay_scraper(
                            search_query=product_info['name'],
                            max_results=10  # limit results per product
                        )
                        
                        if ebay_listings:
                            # convert EbayListing objects to dictionaries
                            listings_data = [
                                {
                                    "title": l.title,
                                    "subtitle": l.subtitle if hasattr(l, 'subtitle') else None,
                                    "price": l.price,
                                    "source_url": str(l.source_url),
                                    "image_url": str(l.image_url) if l.image_url else None,
                                }
                                for l in ebay_listings
                            ]
                            
                            # update listings for this product
                            ebay_repo.update_listings_for_product(
                                product_info['product_id'],
                                listings_data
                            )
                            print(f"  → Found {len(ebay_listings)} eBay listings")
                        else:
                            # still update timestamp even if no listings found
                            idealo_repo.update_last_ebay_check(product_info['product_id'])
                            print(f"  → No eBay listings found")
                    
                    print(f"SUCCESS: Completed eBay checks for {len(needs_ebay_check)} products")
            
            # Save standalone eBay listings (original behavior)
            if listings:
                ebay_repo = EbayListingRepository(conn)
                for listing in listings:
                    ebay_repo.save(listing)
                print(f"SUCCESS: Saved {len(listings)} eBay listings to database")
            
            # commit the transaction
            conn.commit()
            
    except Exception as e:
        logger.error("database_save_failed", error=str(e), exc_info=True)
        print(f"ERROR: Database save failed: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AutoDropshipper Scraper - Unified scraping interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test Idealo scraper (no database)
  python -m src.scrapers.main --scope idealo
  
  # Test eBay scraper (no database)  
  python -m src.scrapers.main --scope ebay --query "gaming laptop"
  
  # Run full production flow (Idealo → DB → eBay checks → DB)
  python -m src.scrapers.main --scope full
        """
    )
    
    parser.add_argument(
        "--scope",
        choices=["idealo", "ebay", "full"],
        required=True,
        help="Scraping scope: 'idealo' (test only), 'ebay' (test only), or 'full' (production with DB)"
    )
    
    parser.add_argument(
        "--query",
        required=False,
        help="Product search query (required for eBay scope)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true", 
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        # reconfigure with DEBUG level
        setup_logging(log_level="DEBUG")
    
    # Get config for eBay scraping
    from src.shared.config.app_settings import get_app_config
    config = get_app_config()
    
    # Welcome message
    subtitle = f"Scope: {args.scope.upper()}"
    if args.scope == "ebay" and args.query:
        subtitle += f" | Query: '{args.query}'"
    elif args.scope == "idealo":
        subtitle += " | Using URL from config"
    elif args.scope == "full":
        subtitle += " | Production Flow"
    
    print("=" * 60)
    print("  AutoDropshipper Scraper")
    print(f"  {subtitle}")
    print("=" * 60)
    
    try:
        if args.scope == "idealo":
            # Test mode: just scrape and log
            products = run_idealo_scraper()
            print(f"\nSUCCESS: Found {len(products)} Idealo products")
            if products:
                print("\nSample products:")
                for i, product in enumerate(products[:5], 1):
                    print(f"  {i}. {product.name[:60]}... - €{product.price}")
            
        elif args.scope == "ebay":
            # Test mode: just scrape and log
            if not args.query:
                print("ERROR: --query is required for eBay scope")
                sys.exit(1)
            
            # Calculate max results from config
            max_results = config.ebay.MAX_BESTMATCH_ITEMS + config.ebay.MAX_LEASTMATCH_ITEMS
            listings = run_ebay_scraper(args.query, max_results)
            
            print(f"\nSUCCESS: Found {len(listings)} eBay listings")
            if listings:
                print("\nSample listings:")
                for i, listing in enumerate(listings[:5], 1):
                    print(f"  {i}. {listing.title[:60]}... - €{listing.price}")
            
        elif args.scope == "full":
            # Production mode: full flow with database
            run_full_production_flow()
            return  # Full flow handles its own output
            
        print("\nScraping completed successfully!")
        
    except KeyboardInterrupt:
        print("\nWARNING: Scraping interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("scraping_failed", error=str(e), exc_info=True)
        print(f"ERROR: Scraping failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()