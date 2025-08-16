"""
Main Idealo scraping orchestration and page navigation.
"""

import time
from typing import List

from seleniumbase import SB

from src.core.exceptions.scraping_errors import PageLoadError, ScrapingError
from src.core.models.idealo_product import IdealoProduct
from src.shared.config.idealo_settings import get_idealo_config
from src.shared.logging.log_setup import get_logger, log_scraping_progress

from .idealo_scraper_utils import IdealoScraperUtils
from .idealo_parser import IdealoParser

logger = get_logger(__name__)


class IdealoScraper:
    """Main class for scraping products from Idealo."""
    
    def __init__(self):
        """Initialize the Idealo scraper."""
        self.config = get_idealo_config()
        self.utils = IdealoScraperUtils()
        self.parser = IdealoParser()
    
    def scrape_products(self) -> List[IdealoProduct]:
        """
        Scrape products from Idealo search results.
        
        Returns:
            List of scraped Idealo products
            
        Raises:
            PageLoadError: If initial page fails to load
            ScrapingError: If scraping process fails
        """
        all_products = []
        max_pages = self.config.MAX_PAGES_TO_SCRAPE
        
        with SB(uc=True, headless=self.config.IS_HEADLESS_IDEALO) as sb:
            try:
                # load initial page
                self._load_initial_page(sb)
                
                # handle cookie consent
                self.utils.handle_cookie_consent(sb)
                
                # scrape products from all pages
                all_products = self._scrape_all_pages(sb, max_pages)
                
            except Exception as e:
                logger.error("scraping_failed", error=str(e), exc_info=True)
                raise ScrapingError(f"Idealo scraping failed: {str(e)}")
        
        logger.info("scraping_completed", total_products=len(all_products))
        return all_products
    
    def _load_initial_page(self, sb) -> None:
        """
        Load the initial Idealo search page.
        
        Args:
            sb: SeleniumBase driver instance
            
        Raises:
            PageLoadError: If page fails to load
        """
        logger.info("loading_initial_page", url=self.config.SCRAPE_URL_IDEALO)
        
        try:
            sb.open(self.config.SCRAPE_URL_IDEALO)
            
            if not self.utils.wait_for_page_load(sb):
                raise PageLoadError(
                    self.config.SCRAPE_URL_IDEALO,
                    "Page failed to load within timeout"
                )
                
        except Exception as e:
            logger.error("initial_page_load_failed", error=str(e))
            raise PageLoadError(self.config.SCRAPE_URL_IDEALO, str(e))
    
    def _scrape_all_pages(self, sb, max_pages: int) -> List[IdealoProduct]:
        """
        Scrape products from all pages.
        
        Args:
            sb: SeleniumBase driver instance
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of scraped products
        """
        all_products = []
        
        for page_num in range(1, max_pages + 1):
            print(f"Scraping page {page_num}/{max_pages}...")
            
            log_scraping_progress(
                logger,
                "scraping_page",
                page=page_num,
                total_pages=max_pages
            )
            
            # scrape current page
            page_products = self._scrape_current_page(sb, page_num)
            all_products.extend(page_products)
            
            print(f"Found {len(page_products)} products on page {page_num}")
            
            # navigate to next page if not the last page
            if page_num < max_pages:
                # add a small delay between pages to avoid rate limiting
                time.sleep(2)
                if not self.utils.navigate_to_next_page(sb):
                    logger.warning("early_pagination_end", page=page_num)
                    break
        
        return all_products
    
    def _scrape_current_page(self, sb, page_num: int) -> List[IdealoProduct]:
        """
        Scrape products from the current page.
        
        Args:
            sb: SeleniumBase driver instance
            page_num: Current page number
            
        Returns:
            List of products from current page
        """
        page_products = []
        
        # scroll to load all products on page
        self.utils.scroll_to_load_products(sb)
        
        # get page content and parse products
        soup = sb.get_beautiful_soup()
        product_elements = self.parser.find_products_on_page(soup)
        
        logger.info("parsing_products", page=page_num, count=len(product_elements))
        
        for element in product_elements:
            try:
                product_data = self.parser.extract_product_data(element)
                if product_data:  # only create product if data was successfully extracted
                    product = IdealoProduct(**product_data)
                    page_products.append(product)
                else:
                    logger.debug("product_skipped", page=page_num, reason="no_data_extracted")
                
            except Exception as e:
                logger.warning(
                    "product_parsing_failed",
                    page=page_num,
                    error=str(e)
                )
                continue
        
        log_scraping_progress(
            logger,
            "page_scraped",
            page=page_num,
            items_found=len(page_products)
        )
        
        return page_products