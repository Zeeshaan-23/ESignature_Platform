# users/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('register/',              views.register,               name='user-register'),
    path('login/',                 views.login,                  name='user-login'),
    path('token/refresh/',         views.token_refresh,          name='token-refresh'),
    path('logout/',                views.logout,                 name='user-logout'),
    path('me/',                    views.me,                     name='user-me'),
    path('password-reset/',        views.password_reset_request, name='password-reset-request'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password-reset-confirm'),
]