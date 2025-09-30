from django.urls import path
from . import views

urlpatterns = [
    # Template endpoints (served via DRF TemplateHTMLRenderer)
    path('', views.home_page, name='home-page'),
    path('login/', views.login_page, name='login-page'),
    path('register/', views.register_page, name='register-page'),
    path("profile/", views.profile_page, name="profile-page"),
    path("support/my-tickets/", views.tickets_page, name="tickets-page"),
    path("support/submit/", views.ticket_submit_page, name="ticket-submit"),
    path("shop/", views.shop_page, name="shop-page"),
    path("products/<slug:slug>/", views.product_page, name="product-page"),
    path('steam-tools-support/', views.steam_support_page,
         name='steam_support_page'),
    path("cart/", views.cart_page, name="cart_page"),
    path("storage/select/", views.storage_pick_page, name="pick_storage"),
    path("orders/", views.orders_page, name="orders-page"),
    path("genie-webhook/", views.genie_webhook, name="genie_webhook"),
    path("payment-done/", views.payment_done_page, name="payment_done_page"),
    path("blog/", views.blog_page, name="blog_page"),
    path("blog/<slug:slug>/", views.blog_detail_page, name="blog_detail_page"),
    path('d-p-calculator/', views.calculator_view, name="calculater"),






    # JSON APIs
    path('api/login/', views.api_login, name='api-login'),
    path('api/register/', views.api_register, name='api-register'),
    path("api/me", views.api_me, name="api-me"),
    path("api/me/update", views.api_me_update, name="api-me-update"),
    path("api/slots/", views.api_reserved_slots, name="api-reserved-slots"),
    path("api/tickets/", views.api_create_ticket, name="api-ticket-create"),
    path("api/my-tickets/", views.api_my_tickets, name="api-my-tickets"),
    path("api/request-game", views.api_request_game, name="api-request-game"),
    path("api/products/", views.api_products, name="api-products"),
    path("api/products/<slug:slug>/",
         views.api_product_detail_by_slug, name="api-product-detail"),
    path("api/genres/", views.api_genres, name="api-genres"),
    path("api/storage-devices/", views.api_storage_devices,
         name="api-storage-devices"),
    path("api/cart/", views.api_cart, name="api_cart"),
    path("api/cart/select-storage/", views.api_cart_select_storage,
         name="api_cart_select_storage"),
    path("api/cart/add-direct/", views.api_cart_add_direct,
         name="api_cart_add_direct"),
    path("api/cart/add-to-device/", views.api_cart_add_to_device,
         name="api_cart_add_to_device"),
    path("api/cart/remove-from-device/", views.api_cart_remove_from_device,
         name="api_cart_remove_from_device"),
    path("api/cart/remove-product/", views.api_remove_product_from_cart,
         name="api_remove_product_from_cart"),
    path("api/cart/remove-storage-device/", views.api_remove_storage_device_from_cart,
         name="api_remove_storage_device_from_cart"),
    path("api/payments/genie/start", views.api_genie_start, name="api-genie-start"),
    path("api/orders/me", views.api_orders_me, name="api-orders-me"),
    path("api/orders/finalize/", views.api_finalize_order_from_customer,
         name="api-orders-finalize"),
    path("api/orders/cod-finalize", views.api_finalize_cod_order_for_user,
         name="api-cod-orders-finalize"),
    path("api/blog/home/", views.api_blog_home, name="api-blog-home"),
    path("api/blog/<slug:slug>/", views.api_blog_detail, name="api_blog_detail"),


]
