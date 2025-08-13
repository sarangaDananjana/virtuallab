from django.urls import path
from . import views

urlpatterns = [
    # Template endpoints (served via DRF TemplateHTMLRenderer)
    path('', views.home_page, name='home-page'),
    path('login/', views.login_page, name='login-page'),
    path('register/', views.register_page, name='register-page'),
    path("support/my-tickets/", views.tickets_page, name="tickets-page"),
    path("support/submit/", views.ticket_submit_page, name="ticket-submit"),



    # JSON APIs
    path('api/login/', views.api_login, name='api-login'),
    path('api/register/', views.api_register, name='api-register'),
    path("api/slots/", views.api_reserved_slots, name="api-reserved-slots"),
    path("api/tickets/", views.api_create_ticket, name="api-ticket-create"),
    path("api/my-tickets/", views.api_my_tickets, name="api-my-tickets"),
    path("api/request-game", views.api_request_game, name="api-request-game"),
]
