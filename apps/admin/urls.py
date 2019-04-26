from django.urls import path
from  . import views
app_name='admin'

urlpatterns = [
    path('',views.IndexView.as_view(),name='index'),
    # path('index_fn/',views.index_fn,name='index_fn'),
    path('tag/', views.NewsTagManageView.as_view(), name='tag'),
    path('tag/<int:tag_id>/', views.NewsTagEditView.as_view(), name='tag_edit'),

    path('pub_news/', views.PubNewsView.as_view(), name='pub_news'),
    path('news_list/',views.NewsManageView.as_view(),name='news_list'),
    path('news/images/',views.UploadFdfs.as_view(),name='images'), #上传到FDFS
    path('token/',views.QiqiuToken.as_view(),name='upload_token'),#上传到骑牛
    path('news_manage_edit/<int:news_id>/',views.NewsManageEditView.as_view(),name='news_manage_edit'),

    path('hotnews_manage/',views.HotNewsView.as_view(),name='hotnews_manage'),
    path('hotnews/add/',views.AddHotNewsView.as_view(),name='hotnews_add'),
    path('hotnews/<int:hotnews_id>/',views.HotNewsEditView.as_view(),name='hotnews_edit'),
    path('tags/<int:tag_id>/news/',views.NewsByTagIdView.as_view(),name='news_by_tagid'),

    path('news/banner/',views.NewsBannerManageView.as_view(),name='news_banner'),
    path('news/banner/<int:banner_id>/',views.BannerEditView.as_view(),name='banner_edit'),
    path('news/add/banner/',views.AddBannerView.as_view(),name='add_banner'),

    path('doc_manage/',views.DocsManageView.as_view(),name='doc_manage'),
    path('doc_pub/',views.DocPubView.as_view(),name='doc_pub'),
    path('doc/<int:doc_id>/',views.DocsEditView.as_view(),name='doc_edit'),
    path('upload/file/',views.DocsUploadFile.as_view(),name='upload_file'),

    path('course/tag/',views.CourseTagsView.as_view(),name='course_tag'),
    path('course/tag/<int:tag_id>/',views.CourseTagsEditView.as_view(),name='course_tag_edit'),
    path('course_manage/',views.CourseManageView.as_view(),name='course_manage'),
    path('course_pub/',views.PubCourseView.as_view(),name='course_pub'),
    path('course/<int:course_id>/',views.CourseEditView.as_view(),name='course_edit'),

    path('user_manage/',views.UserManageView.as_view(),name='user_manage'),
    path('users/<int:user_id>/',views.UserEditView.as_view(),name='users_edit'),
    path('group_manage/',views.UserGroupManageView.as_view(),name='group_manage'),
    path('group/<int:group_id>/',views.GroupEditView.as_view(),name='groups_edit'),
    path('group_add/',views.AddGroupView.as_view(),name='group_add'),

]