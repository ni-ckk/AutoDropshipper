from django.shortcuts import render
from .models import Product

def product_list_view(request):
    products = Product.objects.filter(is_active=True).order_by('-discount_percentage')
    
    context = {
        'products': products
    }
    
    return render(request, 'product_list.html', context)