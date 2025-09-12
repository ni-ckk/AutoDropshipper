"""
eBay selector definitions with fallback support.

This module contains all CSS selectors used by the eBay scraper,
organized by element type with fallback alternatives.
Add new selectors at the beginning of each list for priority.
"""

from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


# selector definitions with fallback alternatives
# first selector in each list is the primary (most recent), others are fallbacks
SELECTORS: Dict[str, List[str]] = {
    # item class identifiers (used for detecting product items)
    'item_class': [
        's-card',      # new eBay structure (2024+)
        's-item',      # old eBay structure (pre-2024)
    ],
    
    # title selectors
    'title': [
        '.s-card__title span',       # new structure
        'div.s-item__title > span',  # old structure
        'h3.s-item__title',          # alternative old structure
        '.s-item__title',            # fallback
    ],
    
    # subtitle selectors (optional field)
    'subtitle': [
        '.s-card__subtitle',     # new structure
        'div.s-item__subtitle',  # old structure
        '.s-item__subtitle',     # fallback
    ],
    
    # price selectors
    'price': [
        '.s-card__price',      # new structure
        'span.s-item__price',  # old structure
        '.s-item__price',      # fallback
    ],
    
    # url/link selectors
    'url': [
        '.su-link',         # new structure
        'a.s-item__link',   # old structure
        '.s-item__link',    # fallback
    ],
    
    # image selectors
    'image': [
        '.s-card__image',        # new structure
        'div.s-item__image img', # old structure
        '.s-item__image img',    # fallback
        'img.s-item__image',     # alternative
    ],
    
    # search results container
    'results_container': [
        'ul.srp-results > li',  # standard selector
    ],
    
    # no results indicator
    'no_results': [
        'div.srp-save-null-search__title',  # standard selector
    ],
    
    # divider for "less relevant results"
    'divider_class': [
        'srp-river-answer--REWRITE_START',  # standard divider class
    ],
    
    # divider text patterns
    'divider_text': [
        'Ergebnisse für weniger Suchbegriffe',  # german
        'Results for fewer search terms',        # english (potential)
    ],
}


class SelectorManager:
    """
    Manages CSS selectors with automatic fallback functionality.
    Tries multiple selectors and caches successful ones for efficiency.
    """
    
    def __init__(self):
        """Initialize the selector manager with caching."""
        # cache successful selectors per session to avoid redundant attempts
        self._successful_selectors: Dict[str, str] = {}
        self._failed_combinations: set = set()  # track what we've tried
        
    def try_selectors(
        self, 
        soup: BeautifulSoup | Tag, 
        selector_key: str,
        required: bool = False
    ) -> Optional[Tag]:
        """
        Try multiple selectors from the fallback list.
        
        Args:
            soup: BeautifulSoup object or Tag to search in
            selector_key: Key from SELECTORS dict (e.g., 'title', 'price')
            required: If True, log error when no selector works
            
        Returns:
            First matching element or None
        """
        # check cache first
        if selector_key in self._successful_selectors:
            cached_selector = self._successful_selectors[selector_key]
            result = soup.select_one(cached_selector)
            if result:
                return result
            # cached selector failed, clear it
            logger.debug(
                "cached_selector_failed",
                key=selector_key,
                selector=cached_selector
            )
            del self._successful_selectors[selector_key]
        
        selectors = SELECTORS.get(selector_key, [])
        if not selectors:
            logger.warning("no_selectors_defined", key=selector_key)
            return None
        
        # try each selector in order
        for selector in selectors:
            # skip if we've already tried this combination
            combo_key = f"{id(soup)}:{selector_key}:{selector}"
            if combo_key in self._failed_combinations:
                continue
                
            try:
                result = soup.select_one(selector)
                if result:
                    # cache successful selector
                    self._successful_selectors[selector_key] = selector
                    if selector != selectors[0]:  # using fallback
                        logger.info(
                            "using_fallback_selector",
                            key=selector_key,
                            selector=selector,
                            index=selectors.index(selector)
                        )
                    return result
                else:
                    self._failed_combinations.add(combo_key)
            except Exception as e:
                logger.debug(
                    "selector_error",
                    key=selector_key,
                    selector=selector,
                    error=str(e)
                )
                self._failed_combinations.add(combo_key)
        
        # no selector worked
        if required:
            logger.error(
                "all_selectors_failed",
                key=selector_key,
                tried_count=len(selectors)
            )
        else:
            logger.debug(
                "no_matching_element",
                key=selector_key,
                tried_count=len(selectors)
            )
        
        return None
    
    def try_class_match(
        self,
        element: Tag,
        class_key: str = 'item_class'
    ) -> bool:
        """
        Check if element's class matches any of the patterns.
        
        Args:
            element: BeautifulSoup Tag to check
            class_key: Key from SELECTORS dict for class patterns
            
        Returns:
            True if any class pattern matches
        """
        class_list = element.get('class')
        if not isinstance(class_list, list):
            return False
        
        patterns = SELECTORS.get(class_key, [])
        for pattern in patterns:
            if pattern in class_list:
                if pattern != patterns[0]:  # using fallback
                    logger.debug(
                        "using_fallback_class_pattern",
                        pattern=pattern,
                        index=patterns.index(pattern)
                    )
                return True
        
        return False
    
    def get_all_patterns(self, pattern_key: str) -> List[str]:
        """
        Get all patterns for a given key (e.g., for checking text patterns).
        
        Args:
            pattern_key: Key from SELECTORS dict
            
        Returns:
            List of patterns
        """
        return SELECTORS.get(pattern_key, [])
    
    def clear_cache(self):
        """Clear the selector cache (useful when page structure changes)."""
        self._successful_selectors.clear()
        self._failed_combinations.clear()
        logger.debug("selector_cache_cleared")


# global instance for reuse across parser calls
selector_manager = SelectorManager()