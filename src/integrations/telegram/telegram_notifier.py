"""
Telegram notifier for profitable deals after database save.
"""

from typing import List, Optional
from decimal import Decimal

from src.core.models.ebay_listing import EbayListing
from src.core.models.idealo_product import IdealoProduct
from src.core.models.product_comparison import ProductComparison
from src.integrations.telegram.telegram_client import TelegramClient
from src.integrations.telegram.telegram_formatter import TelegramFormatter
from src.shared.config.telegram_settings import get_telegram_config
from src.shared.config.ebay_settings import get_ebay_config
from src.shared.logging.log_setup import get_logger

logger = get_logger(__name__)


class TelegramNotifier:
    """Handles profitable deal notifications after database save."""
    
    def __init__(self):
        """Initialize notifier with client and formatter."""
        self.client = TelegramClient()
        self.formatter = TelegramFormatter()
        self.telegram_config = get_telegram_config()
        self.ebay_config = get_ebay_config()
    
    def send_profitable_deal_notification(
        self,
        idealo_product: IdealoProduct,
        ebay_listings: List[EbayListing],
        comparison: ProductComparison
    ) -> bool:
        """
        Send notification for profitable deal after DB save.
        
        Args:
            idealo_product: The Idealo product found to be profitable
            ebay_listings: List of eBay listings for comparison
            comparison: ProductComparison object with profit calculations
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        # only send if profitable
        if not comparison.is_profitable:
            logger.debug(
                "notification_skipped_not_profitable",
                product=idealo_product.name,
                potential_profit=comparison.potential_profit
            )
            return False
        
        # check telegram is configured
        if not self.telegram_config.is_configured:
            logger.debug("telegram_not_configured", action="skip_notification")
            return False
        
        try:
            # build comparison data using the formatter's helper method
            comparison_data = self.formatter.build_comparison_data(
                idealo_product, 
                ebay_listings, 
                self.ebay_config.MAX_BESTMATCH_ITEMS,
                self.ebay_config.MAX_LEASTMATCH_ITEMS
            )
            
            # add profitability info to the message
            comparison_data['is_profitable'] = comparison.is_profitable
            comparison_data['potential_profit'] = comparison.potential_profit
            comparison_data['min_ebay_price'] = comparison.min_ebay_price
            
            logger.info(
                "telegram_comparison_data_built", 
                best_count=len(comparison_data.get('best_matches', [])),
                less_relevant_count=len(comparison_data.get('less_relevant_matches', [])),
                is_profitable=comparison.is_profitable,
                potential_profit=comparison.potential_profit
            )
            
            # format the message
            message = self.formatter.format_ebay_results(comparison_data)
            
            # add profit header to message
            profit_header = (
                f"💰 <b>PROFITABLE DEAL FOUND!</b>\n"
                f"<b>Potential Profit: €{comparison.potential_profit}</b>\n"
                f"<b>Min eBay Price: €{comparison.min_ebay_price}</b>\n"
                f"<b>Profit Margin: {comparison.profit_percentage:.1f}%</b>\n\n"
            )
            message = profit_header + message
            
            # validate message before sending
            if not message or not message.strip():
                logger.error(
                    "telegram_message_empty", 
                    comparison_data=comparison_data,
                    idealo_product=idealo_product.name
                )
                message = f"Profitable deal found for {idealo_product.name} with {len(ebay_listings)} listings, but message formatting failed."
            
            # send notification
            if self.client.send_notification(message):
                logger.info(
                    "telegram_profitable_notification_sent", 
                    product=idealo_product.name, 
                    listings_count=len(ebay_listings),
                    potential_profit=comparison.potential_profit,
                    profit_percentage=comparison.profit_percentage
                )
                return True
            else:
                logger.warning(
                    "telegram_notification_failed",
                    product=idealo_product.name
                )
                return False
                
        except Exception as e:
            logger.error(
                "telegram_notification_error",
                error=str(e),
                product=idealo_product.name,
                exc_info=True
            )
            # don't fail the whole process if telegram fails
            return False
    
    def check_duplicate_notification(
        self,
        product_id: int,
        potential_profit: Decimal,
        threshold_hours: int = 24
    ) -> bool:
        """
        Check if we've already sent a notification for this product/profit recently.
        
        This is a placeholder for future implementation to avoid duplicate notifications.
        Could track in database or cache.
        
        Args:
            product_id: Product ID to check
            potential_profit: Current profit amount
            threshold_hours: Hours to consider as "recent"
            
        Returns:
            True if duplicate notification, False if ok to send
        """
        # TODO: Implement duplicate check logic
        # for now, always allow notifications
        return False