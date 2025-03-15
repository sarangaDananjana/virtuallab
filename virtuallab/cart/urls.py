from django.urls import path
from . import views


urlpatterns = [
    path('orders/', views.orders, name='orders'),
    path('', views.cart_view, name='cart'),
    path('order_success/', views.order_success, name='order_success'),
    path('checkout/', views.checkout, name='checkout')
]
