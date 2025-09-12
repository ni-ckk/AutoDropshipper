from django.shortcuts import render
from .models import Product

def product_list_view(request):
    products = Product.objects.filter(is_active=True).order_by('-discount').prefetch_related('ebay_listings')
    
    context = {
        'products': products
    }
    
    return render(request, 'product_list.html', context)

def profitable_deals_view(request):
    """
    Display products sorted by potential profit from highest to lowest.
    Only shows products with positive profit potential.
    This is a READ-ONLY view - profit calculations are done during scraping.
    """
    # just query for profitable products (no calculations, no database writes)
    profitable_products = Product.objects.filter(
        is_active=True,
        is_profitable=True,
        potential_profit__isnull=False
    ).order_by('-potential_profit').prefetch_related(
        'ebay_listings'
    )
    
    context = {
        'products': profitable_products
    }
    
    return render(request, 'profitable_deals.html', context)