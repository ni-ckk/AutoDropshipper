from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('tolko-dlya-pacanov/', admin.site.urls),
    path('', include('deal_board.urls')),
]
