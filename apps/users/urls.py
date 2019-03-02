from django.urls import path
from . import views
app_name='users'

urlpatterns = [
    path('login/',views.LoginView.as_view(),name='login'),
    path('logput/',views.LogoutView.as_view(),name='logout'),
    path('register/',views.RegisterView.as_view(),name='register')
]