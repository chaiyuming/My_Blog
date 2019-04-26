"""My_Blog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', include('apps.admin.urls')),
    path('', include('apps.news.urls')),
    path('course/', include('apps.course.urls')),
    path('docs/', include('apps.doc.urls')),
    path('users/', include('apps.users.urls')),
    path('', include('apps.verification.urls')),
    path('ueditor/',include('apps.ueditor.urls')),
]+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
# settings.MRDIA_URL表示当django访问MEDIA_URL='/media/'文件时，那么就到settings.MEDIA_ROOT目录下去访问。
# static是一个列表 ，