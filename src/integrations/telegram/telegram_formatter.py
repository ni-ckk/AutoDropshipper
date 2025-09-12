"""
Format product comparisons into Telegram-friendly messages.
"""

from decimal import Decimal
from typing import Any, Dict, List

from src.core.models.ebay_listing import EbayListing
from src.core.models.idealo_product import IdealoProduct
from src.core.utils.profitability_calculator import ProfitabilityCalculator
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class TelegramFormatter:
    """Formats scraper results for Telegram messages."""
    
    @staticmethod
    def format_ebay_results(results: Dict[str, Any]) -> str:
        """
        Format eBay scraper results for Telegram message (original logic preserved).
        
        Args:
            results: Dictionary with eBay scraper results
            
        Returns:
            Formatted message string
        """
        try:
            # safely get the product title with fallback
            product_title = results.get('idealo_product_title', 'Unknown Product')
            if not product_title:
                product_title = 'Unknown Product'
            
            # escape HTML special characters to prevent parsing issues
            product_title = str(product_title).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # get idealo URL if provided
            idealo_url = results.get('idealo_product_url')
            if idealo_url:
                # make the product name a clickable link
                product_title_with_link = f"<a href='{idealo_url}'>{product_title}</a>"
            else:
                product_title_with_link = product_title
            
            message = f"<b>🔎 Scrape Results for:</b> {product_title_with_link}\n\n"

            if results.get('best_matches'):
                message += "<b>✅ Best Matches:</b>\n"
                for item in results.get('best_matches', []):
                    try:
                        # safely get item fields with defaults
                        title = str(item.get('Ebay product title', 'Unknown')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        link = str(item.get('Ebay product link', '#'))
                        price = float(item.get('Ebay product price', 0))
                        profit = float(item.get('potential_profit', 0))
                        
                        profit_text = f"pot. Profit: <b>€{profit:.2f}</b>"
                        message += f"- <a href='{link}'>{title}</a>\n"
                        message += f"  Price: €{price:.2f} | {profit_text}\n\n"
                    except Exception as e:
                        logger.warning("format_item_failed", error=str(e), item=item)
                        continue
            else:
                message += "❌ No best matches found.\n\n"

            if results.get('less_relevant_matches'):
                message += "<b>🤔 Less Relevant Matches:</b>\n"
                for item in results.get('less_relevant_matches', []):
                    try:
                        # safely get item fields with defaults
                        title = str(item.get('Ebay product title', 'Unknown')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        link = str(item.get('Ebay product link', '#'))
                        price = float(item.get('Ebay product price', 0))
                        profit = float(item.get('potential_profit', 0))
                        
                        profit_text = f"pot. Profit: <b>€{profit:.2f}</b>"
                        message += f"- <a href='{link}'>{title}</a>\n"
                        message += f"  Price: €{price:.2f} | {profit_text}\n\n"
                    except Exception as e:
                        logger.warning("format_item_failed", error=str(e), item=item)
                        continue

            # ensure message is never empty
            if not message or len(message.strip()) == 0:
                message = "eBay search completed but no results could be formatted."
                
            logger.debug("telegram_message_formatted", length=len(message), content_preview=message[:100])
            return message
            
        except Exception as e:
            logger.error("format_ebay_results_failed", error=str(e), results=results)
            # return a fallback message instead of raising
            return f"eBay search completed but formatting failed: {str(e)}"
    
   
    @staticmethod
    def build_comparison_data(
        idealo_product: IdealoProduct,
        ebay_listings: List[EbayListing],
        max_best_matches: int = 5,
        max_least_matches: int = 3
    ) -> Dict[str, Any]:
        """
        Build comparison data structure for format_ebay_results.
        
        Args:
            idealo_product: The Idealo product to compare
            ebay_listings: List of eBay listings to compare against
            max_best_matches: Maximum number of best matches to include
            max_least_matches: Maximum number of least matches to include
            
        Returns:
            Dictionary formatted for format_ebay_results method
        """
        try:
            # ensure we have valid product data
            product_name = idealo_product.name if idealo_product and hasattr(idealo_product, 'name') else 'Unknown Product'
            product_price = idealo_product.price if idealo_product and hasattr(idealo_product, 'price') else Decimal('0')
            
            # ensure product_name is not None or empty
            if not product_name:
                product_name = 'Unknown Product'
            
            # separate listings based on is_best_match attribute
            best_matches = []
            less_relevant = []
            
            if ebay_listings:
                for listing in ebay_listings:
                    if hasattr(listing, 'is_best_match') and listing.is_best_match:
                        best_matches.append(listing)
                    else:
                        less_relevant.append(listing)
            
            # initialize result structure with guaranteed fields
            result = {
                'idealo_product_title': f"{product_name} - €{product_price:.2f}",
                'idealo_product_url': str(idealo_product.source_url) if idealo_product and hasattr(idealo_product, 'source_url') else None,
                'best_matches': [],
                'less_relevant_matches': []
            }
            
            # calculate profitability
            calc = ProfitabilityCalculator()
            
            # process best matches
            for listing in best_matches[:max_best_matches]:
                try:
                    profit = calc.calculate_simple_profit(
                        product_price,
                        listing.price if hasattr(listing, 'price') else Decimal('0')
                    )
                    result['best_matches'].append({
                        'Ebay product title': listing.title if hasattr(listing, 'title') else 'Unknown',
                        'Ebay product link': str(listing.source_url) if hasattr(listing, 'source_url') else '#',
                        'Ebay product price': float(listing.price) if hasattr(listing, 'price') else 0,
                        'potential_profit': float(profit)
                    })
                except Exception as e:
                    logger.warning("process_best_match_failed", error=str(e), listing=listing)
                    continue
            
            # process least relevant matches
            for listing in less_relevant[:max_least_matches]:
                try:
                    profit = calc.calculate_simple_profit(
                        product_price,
                        listing.price if hasattr(listing, 'price') else Decimal('0')
                    )
                    result['less_relevant_matches'].append({
                        'Ebay product title': listing.title if hasattr(listing, 'title') else 'Unknown',
                        'Ebay product link': str(listing.source_url) if hasattr(listing, 'source_url') else '#',
                        'Ebay product price': float(listing.price) if hasattr(listing, 'price') else 0,
                        'potential_profit': float(profit)
                    })
                except Exception as e:
                    logger.warning("process_less_relevant_failed", error=str(e), listing=listing)
                    continue
            
            logger.info(
                "comparison_data_built",
                idealo_product=product_name,
                best_matches_count=len(result['best_matches']),
                less_relevant_count=len(result['less_relevant_matches']),
                title_set=result.get('idealo_product_title', 'MISSING')
            )
            
            return result
            
        except Exception as e:
            logger.error("build_comparison_data_failed", error=str(e))
            # return minimal valid structure
            return {
                'idealo_product_title': 'Error Processing Product',
                'best_matches': [],
                'less_relevant_matches': []
            }