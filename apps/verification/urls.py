from django.urls import path,re_path
from . import views
app_name='verification'

urlpatterns = [
    path('image_captcha/<uuid:image_code_id>/', views.ImageCaptcha.as_view(), name='image_captcha'),
    re_path('username/(?P<username>\w{5,20})/', views.CheckUsernameView.as_view(), name='check_username'),
]