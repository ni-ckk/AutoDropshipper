from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list_view, name='product_list'),
    path('profitable-deals/', views.profitable_deals_view, name='profitable_deals'),
]
