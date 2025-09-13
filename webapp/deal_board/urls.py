from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/profitable-deals/', permanent=False), name='home'),
    path('all-products/', views.product_list_view, name='product_list'),
    path('profitable-deals/', views.profitable_deals_view, name='profitable_deals'),
]
