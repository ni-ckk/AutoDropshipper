from django.contrib import admin
from .models import Product, PriceLog

admin.site.register(Product)
admin.site.register(PriceLog)