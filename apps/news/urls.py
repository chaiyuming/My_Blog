from django.urls import path
from . import views
app_name='news'

urlpatterns = [
    path('',views.IndexView.as_view(),name='index'),
    path('news_list/',views.NewslistView.as_view(),name='news_list'),
    path('news_detail/<int:news_id>/',views.NewsDetailView.as_view(),name='news_detail'),
    path('news/<int:news_id>/comment/',views.CommentView.as_view(),name='comment'),
    path('search/',views.SearchView(),name='search'),
]