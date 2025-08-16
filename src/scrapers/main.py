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


def run_full_comparison(min_profit_margin: Decimal = Decimal("50.0")) -> None:
    """
    Run full product comparison workflow: Idealo → eBay → Profitability Analysis.
    
    Uses the URL from SCRAPE_URL_IDEALO for Idealo scraping.
    
    Args:
        min_profit_margin: Minimum profit margin percentage required
    """
    print("=" * 60)
    print("  AutoDropshipper Full Comparison")
    print("  Using Idealo URL from config")
    print(f"  Min Profit Margin: {min_profit_margin}%")
    print("=" * 60)
    
    # Step 1: Scrape Idealo products
    print("Step 1: Scraping Idealo products...")
    idealo_products = run_idealo_scraper()
    
    if not idealo_products:
        print("ERROR: No Idealo products found. Stopping.")
        return
    
    # derive search query from first product or category
    if idealo_products:
        # use the category from first product for eBay search
        search_query = idealo_products[0].category if idealo_products[0].category else "electronics"
    else:
        search_query = "electronics"  # fallback
        
    # Step 2: Scrape eBay listings  
    print("Step 2: Scraping eBay listings for comparison...")
    ebay_listings = run_ebay_scraper(search_query, max_results=20)
    
    if not ebay_listings:
        print("ERROR: No eBay listings found. Stopping.")
        return
    
    # Step 3: Analyze profitability
    print("Step 3: Analyzing profitability...")
    profitable_products = []
    
    for product in idealo_products:
        comparison = ProductComparison(
            idealo_product=product,
            ebay_listings=ebay_listings
        )
        
        comparison.calculate_profitability(min_profit_margin=min_profit_margin)
        
        if comparison.is_profitable:
            profitable_products.append(comparison)
            print(
                f"✓ {product.name[:50]}... - "
                f"€{product.price} → €{comparison.min_ebay_price} "
                f"({comparison.profit_percentage:.1f}% margin)"
            )
    
    # Display results
    if profitable_products:
        print("=" * 60)
        print("  Analysis Complete")
        print(f"  Found {len(profitable_products)} profitable products!")
        print(f"  Total Idealo products analyzed: {len(idealo_products)}")
        print(f"  Total eBay listings found: {len(ebay_listings)}")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  Analysis Complete")
        print("  No profitable products found.")
        print("  Try lowering the minimum profit margin or different search terms.")
        print("=" * 60)


def save_to_database(products: List[IdealoProduct], listings: List[EbayListing]) -> None:
    """
    Save scraped data to database.
    
    Args:
        products: Idealo products to save
        listings: eBay listings to save
    """
    from src.database.handlers.connection_handler import ConnectionHandler
    
    try:
        with ConnectionHandler() as conn:
            # Save Idealo products
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
                idealo_repo.process_scraped_products(products_data)
                print(f"SUCCESS: Saved {len(products)} Idealo products to database")
            
            # Save eBay listings
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
  # Run Idealo scraper (uses URL from SCRAPE_URL_IDEALO and MAX_PAGES_TO_SCRAPE from .env)
  python -m src.scrapers.main --platform idealo --save
  
  # Run eBay scraper (requires query)  
  python -m src.scrapers.main --platform ebay --query "gaming laptop" --max-results 30
  
  # Run full comparison analysis (Idealo URL + eBay search)
  python -m src.scrapers.main --platform both --min-profit 25
  
  # Save Idealo results to database
  python -m src.scrapers.main --platform idealo --save
        """
    )
    
    parser.add_argument(
        "--platform",
        choices=["idealo", "ebay", "both"],
        required=True,
        help="Which platform to scrape"
    )
    
    parser.add_argument(
        "--query",
        required=False,
        help="Product search query (only for eBay, Idealo uses URL from config)"
    )
    
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum number of results to scrape (only for eBay, default: 20)"
    )
    
    parser.add_argument(
        "--min-profit",
        type=float,
        default=50.0,
        help="Minimum profit margin percentage for 'both' mode (default: 50.0)"
    )
    
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to database"
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
    
    # Welcome message
    subtitle = f"Platform: {args.platform.upper()}"
    if args.platform == "ebay" and args.query:
        subtitle += f" | Query: '{args.query}'"
    elif args.platform == "idealo":
        subtitle += " | Using URL from config"
    
    print("=" * 60)
    print("  AutoDropshipper Scraper")
    print(f"  {subtitle}")
    print("=" * 60)
    
    try:
        products: List[IdealoProduct] = []
        listings: List[EbayListing] = []
        
        if args.platform == "idealo":
            products = run_idealo_scraper()
            print(f"SUCCESS: Found {len(products)} Idealo products")
            
        elif args.platform == "ebay":
            if not args.query:
                print("ERROR: --query is required for eBay scraping")
                sys.exit(1)
            listings = run_ebay_scraper(args.query, args.max_results)  
            print(f"SUCCESS: Found {len(listings)} eBay listings")
            
        elif args.platform == "both":
            run_full_comparison(Decimal(str(args.min_profit)))
            return  # Full comparison handles its own output
        
        # Save to database if requested
        if args.save and (products or listings):
            save_to_database(products, listings)
            
        print("SUCCESS: Scraping completed successfully!")
        
    except KeyboardInterrupt:
        print("\nWARNING: Scraping interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("scraping_failed", error=str(e), exc_info=True)
        print(f"ERROR: Scraping failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()