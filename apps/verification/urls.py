from django.urls import path,re_path
from . import views
app_name='verification'

urlpatterns = [
    path('image_captcha/<uuid:image_code_id>/', views.ImageCaptcha.as_view(), name='image_captcha'),
    path('sms_codes/', views.SmsCaptcha.as_view(), name='sms_codes'),
    re_path('username/(?P<username>\w{5,20})/', views.CheckUsernameView.as_view(), name='check_username'),
    re_path('telephone/(?P<telephone>1[3-9]\d{9})/',views.CheckTelephoneView.as_view(),name='check_telephone'),
]