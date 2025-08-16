from django.shortcuts import render
from .models import Product

def product_list_view(request):
    products = Product.objects.filter(is_active=True).order_by('-discount').prefetch_related('ebay_listings')
    
    context = {
        'products': products
    }
    
    return render(request, 'product_list.html', context)