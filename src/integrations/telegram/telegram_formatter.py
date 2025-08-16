"""
Format product comparisons into Telegram-friendly messages.
"""

from typing import Any, Dict, List

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
        message = f"<b>🔎 Scrape Results for:</b> {results['idealo_product_title']}\n\n"

        if results.get('best_matches'):
            message += "<b>✅ Best Matches:</b>\n"
            for item in results['best_matches']:
                profit = f"pot. Profit: <b>€{item['potential_profit']:.2f}</b>"
                message += f"- <a href='{item['Ebay product link']}'>{item['Ebay product title']}</a>\n"
                message += f"  Price: €{item['Ebay product price']} | {profit}\n\n"
        else:
            message += "❌ No best matches found.\n\n"

        if results.get('less_relevant_matches'):
            message += "<b>🤔 Less Relevant Matches:</b>\n"
            for item in results['less_relevant_matches']:
                profit = f"pot. Profit: <b>€{item['potential_profit']:.2f}</b>"
                message += f"- <a href='{item['Ebay product link']}'>{item['Ebay product title']}</a>\n"
                message += f"  Price: €{item['Ebay product price']} | {profit}\n\n"

        logger.debug("telegram_message_formatted", length=len(message))
        return message
    
    @staticmethod
    def format_profitable_products(products: List[Dict[str, Any]]) -> str:
        """
        Format list of profitable products for Telegram.
        
        Args:
            products: List of profitable product dictionaries
            
        Returns:
            Formatted message string
        """
        if not products:
            return "📊 <b>No profitable products found in this scraping session.</b>"
        
        message = f"💰 <b>Found {len(products)} Profitable Products!</b>\n\n"
        
        for i, product in enumerate(products[:5], 1):  # limit to top 5
            message += f"<b>{i}. {product['name'][:50]}</b>\n"
            message += f"💰 Profit: €{product.get('profit', 0):.2f}\n"
            message += f"🏪 Idealo: €{product['price']}\n"
            if product.get('source_url'):
                message += f"🔗 <a href='{product['source_url']}'>View Product</a>\n\n"
        
        if len(products) > 5:
            message += f"... and {len(products) - 5} more products.\n"
        
        return message
    
    @staticmethod
    def format_scraping_summary(
        total_products: int,
        profitable_count: int,
        scrape_duration: str = ""
    ) -> str:
        """
        Format scraping session summary.
        
        Args:
            total_products: Total products scraped
            profitable_count: Number of profitable products found
            scrape_duration: Duration of scraping session
            
        Returns:
            Formatted summary message
        """
        message = "📈 <b>Scraping Session Complete!</b>\n\n"
        message += f"📦 Total Products: {total_products}\n"
        message += f"💰 Profitable: {profitable_count}\n"
        
        if total_products > 0:
            profit_rate = (profitable_count / total_products) * 100
            message += f"📊 Success Rate: {profit_rate:.1f}%\n"
        
        if scrape_duration:
            message += f"⏱️ Duration: {scrape_duration}\n"
        
        return message