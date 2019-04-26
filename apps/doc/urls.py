from django.urls import path
from . import views
app_name='doc'

urlpatterns = [
    path('',views.Docfile,name='index'),
    path('doc/<int:doc_id>/',views.DocDownload.as_view(),name='doc_down'),

]