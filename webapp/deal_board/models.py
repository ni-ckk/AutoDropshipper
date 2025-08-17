from django.db import models

class Product(models.Model):
    """
    product main info model
    """
    name = models.CharField(max_length=500, help_text="The name of the product.")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="The current price of the product.")
    discount = models.IntegerField(help_text="Discount percentage")
    source_url = models.URLField(max_length=1024, unique=True, help_text="The unique URL of the product on the source website.")
    image_url = models.URLField(max_length=1024, null=True, blank=True, help_text="URL of the product's image.")
    is_active = models.BooleanField(default=True, help_text="Is the product currently available on the source site?")
    category = models.CharField(max_length=100, default="Unknown", help_text="Product category (defaults to 'Unknown' if extraction fails).")
    last_ebay_check = models.DateTimeField(null=True, blank=True, help_text="Last time eBay listings were checked for this product.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PriceLog(models.Model):
    """
    logs every price point scraped for a product to track its history.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_logs")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="The price recorded at the time of scraping.")
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - €{self.price} on {self.scraped_at.strftime('%Y-%m-%d')}"

class EbayListing(models.Model):
    """
    stores a Ebay info of a scraped product that are similar
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ebay_listings")
    
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    source_url = models.URLField(max_length=1024)
    image_url = models.URLField(max_length=1024, null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for €{self.price}"