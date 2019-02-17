from django.urls import path
from . import views
app_name='users'

urlpatterns = [
    path('login/',views.Login,name='login'),
    path('register/',views.Register,name='register')
]