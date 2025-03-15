from django.urls import path
from . import views


urlpatterns = [path('search/', views.search_games, name='search'),
    path('', views.games_shop, name='shop'),
    path('select_storage_device/', views.select_storage_device,
         name="select_storage_device"),
    path('<slug:slug>/', views.game_detail, name='product_detail'),

]
