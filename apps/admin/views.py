import json
import logging
import qiniu

from collections import OrderedDict
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage
from urllib import parse
from django.db.models import Q
from django.conf import settings
from django.shortcuts import render, HttpResponse, Http404
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import ContentType, Permission, Group

from apps.news import models
from apps.doc.models import Doc
from apps.users.models import User
from apps.course.models import Course,CourseCategory,Teacher
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from utils.paginator_script import get_paginator_data
from utils.fastdfs.fdfs import FDFS_Client
from . import constants, forms
from apps.news.constants import SHOW_HOTNEWS_COUNT

logger = logging.getLogger('django')


# Create your views here.
# 装饰器
def my_decorator(func):
    def wrapper(request, *args, **kwargs):
        print('判断用户是否登录，是否有相关权限')
        return func(request, *args, **kwargs)

    return wrapper


# @my_decorator
# def index_fn(request):
#     print('333333')
#     return HttpResponse('白天不懂夜的黑')
@method_decorator([staff_member_required(login_url='/')],name='dispatch')
# class IndexView(LoginRequiredMixin, View):
class IndexView(View):
    def get(self, request):
        '''
        create admin index  view
        :param request:
        :return:
        '''
        return render(request, 'admin/index/index.html')

class NewsTagManageView(PermissionRequiredMixin, View):
    permission_required = ('news.add_tag', 'news.view_tag')
    # 如果raise_exception给出参数，则装饰器将引发 PermissionDenied，提示403（HTTP Forbidden）视图而不是重定向到登录页面
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(NewsTagManageView, self).handle_no_permission()

    def get(self, request):
        '''
        create add news tag info views
        :param request:
        :return:
        '''
        # annotate()级联查询
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).filter(
            is_delete=False).order_by('-num_news', '-update_time')
        return render(request, 'admin/news/news_tag.html', locals())

    def post(self, request):
        # 1、从前端获取数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')
        # 2、校验
        if tag_name:
            tag_name = tag_name.strip()
            # get_or_create()如果没有就会自动创建，返回一个新的实列对象，以及True组成的元祖。
            # 如果查找到一个对象，get_or_create() 返回一个包含匹配到的对象以及False 组成的元组。
            # 3、保存到数据库
            tag_tuple, tag_boolean = models.Tag.objects.get_or_create(name=tag_name)
            # news_tag_dict可以不写
            news_tag_dict = {
                'id': tag_tuple.id,
                'name': tag_tuple.name
            }
            # 4、返回执行结果
            return to_json_data(errmsg='标签创建成功！', data=news_tag_dict) if tag_boolean else to_json_data(
                errno=Code.DATAEXIST, errmsg='标签已存在，请重新输入！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签名不能为空！')

class NewsTagEditView(PermissionRequiredMixin, View):
    permission_required = ('news.change_tag', 'news.delete_tag')
    # 如果raise_exception给出参数，则装饰器将引发 PermissionDenied，提示403（HTTP Forbidden）视图而不是重定向到登录页面
    raise_exception = True

    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')

    def delete(self, request, tag_id):
        '''
        delete tag
        :param request:
        :param tag_id:
        :return: /tag/<int:tag_id>/
        '''
        tag = models.Tag.objects.only('id').filter(id=tag_id, is_delete=False).first()
        if tag:
            tag.is_delete = True
            tag.save(update_fields=['is_delete'])
            return to_json_data(errno=Code.OK, errmsg='标签删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='您删除的标签不存在')

    def put(self, request, tag_id):
        '''
        delete the tag
        :param request:
        :param tag_id:
        :return:
        '''
        try:
            json_data = request.body
            if not json_data:
                return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
            dict_data = json.loads(json_data.decode('utf8'))
            tag_name = dict_data.get('name')
        except Exception as e:
            return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])
        tag = models.Tag.objects.only('id').filter(is_delete=False, id=tag_id).first()
        if tag:
            # .strip()去除空格，前提是先确认tag_name是否存在
            tag_name = tag_name.strip()
            if tag_name:
                exist = models.Tag.objects.only('id').filter(is_delete=False, name=tag_name).exists()
                if not exist:
                    tag.name = tag_name
                    tag.save(update_fields=['name'])
                    return to_json_data(errmsg='标签更新成功！')
                else:
                    return to_json_data(errno=Code.PARAMERR, errmsg='标签已存在！')

            else:
                return to_json_data(errno=Code.PARAMERR, errmsg='标签名不能为空！')
        else:
            return to_json_data(errno=Code.NODATA, errmsg='标签不存在！')

class PubNewsView(PermissionRequiredMixin, View):
    '''
    create news pub view
    route:/admin/pub_news/
    '''
    permission_required = ('news.add_news', 'news.view_news')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(PubNewsView, self).handle_no_permission()

    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/pub_news.html', locals())

    def post(self, request):
        # 1、从前端获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        # 2、校验
        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            # 3、保存到数据库
            # n = models.News(**form.cleaned_data)
            # n.title = form.cleaned_data.get('title')
            #
            # n.save()
            news_instance = form.save(commit=False)
            news_instance.author = request.user
            # news_instance.author_id = 1     # for test
            news_instance.save()
            # 4、返回执行结果
            return to_json_data(errmsg='文章创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class NewsManageView(View):
    '''
    create news list manage View
    route:/admin/news_manage
    '''
    permission_required = ('news.add_news', 'news.view_news')
    raise_exception = True

    def get(self, request):
        newes = models.News.objects.only('id', 'title', 'tag__name', 'author__username', 'update_time').select_related(
            'tag', 'author').filter(is_delete=False)
        # 如果传入的时间格式错误那么在strptime（）就会报错，此时就需要捕获异常。
        try:
            start = request.GET.get('start', '')
            # start和end是字符串,需要转换成时间格式
            start = datetime.strptime(start, '%Y/%m/%d') if start else ''
            end = request.GET.get('end', '')
            end = datetime.strptime(end, '%Y/%m/%d') if end else ''
        except Exception as e:
            logger.info('时间格式错误:{}'.format(e))
            start = end = ''

        if start and not end:
            newes = newes.filter(update_time__lte=start)
        if end and not start:
            newes = newes.filter(update_time__gte=end)
        if end and start:
            newes = newes.filter(update_time__range=(end, start))

        title = request.GET.get('title', '')
        if title:
            newes = newes.filter(title__contains=title)
        author = request.GET.get('author', '')
        if author:
            newes = newes.filter(author__username__icontains=author)

        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.info("标签错误：\n{}".format(e))
            tag_id = 0
        if tag_id != 0:
            newes = newes.filter(tag_id=tag_id)
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info('新闻页数格式错误：{}'.format(e))
            page = 1
        # 创建对象
        paginator = Paginator(newes, constants.PER_PAGE_NEWS_COUNT)
        # 某一页的数据
        try:
            page_object = paginator.page(page)
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logger.info('用户访问的页数大于总页数')
            page_object = paginator.page(paginator.num_pages)
        # 调用get_data_pagination函数
        data_pagination = get_paginator_data(paginator, page_object)
        # 转换成字符串格式
        start = start.strftime('%Y/%m/%d') if start else ''
        end = end.strftime('%Y/%m/%d') if end else ''
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        context = {
            'start': start,
            'end': end,
            'paginator': paginator,
            'title': title,
            'tags': tags,
            'author': author,
            'tag_id': tag_id,
            'page_object': page_object,
            'newes': page_object.object_list,
            'url_paramter': parse.urlencode({
                'start': start,
                'end': end,
                'title': title,
                'tag_id': tag_id,
                'author': author,
            })
        }
        context.update(data_pagination)
        return render(request, 'admin/news/news_list_manage.html', context=context)

class NewsManageEditView(PermissionRequiredMixin, View):
    permission_required = ('news.change_news', 'news.delete_news')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(NewsManageEditView, self).handle_no_permission()

    def get(self, request, news_id):
        """
        获取待编辑的文章
        """
        news = models.News.objects.only('id').filter(is_delete=False, id=news_id).first()
        if news:
            tags = models.Tag.objects.only('id').filter(is_delete=False)
            context = {
                'news': news,
                'tags': tags
            }
            return render(request, 'admin/news/pub_news.html', context=context)
        else:
            raise Http404('您访问的新闻不存在！')

    def delete(self, request, news_id):
        '''
        create news delete view
        :param request:
        :param news_id:
        :return:/admin/news_manage/<int:news_id>/
        '''
        news = models.News.objects.only('id').filter(id=news_id, is_delete=False).first()
        if news:
            news.is_delete = True
            news.save(update_fields=['is_delete'])
            return to_json_data(errmsg='新闻删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='你要删除的新闻不存在！')

    def put(self, request, news_id):
        '''
        create news list manage edit view
        :param request:
        :param news_id:
        :return: /admin/news_manage/<int:news_id>/
        '''
        news = models.News.objects.only('id').filter(id=news_id, is_delete=False).first()
        if not news:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的文章不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.image_url = form.cleaned_data.get('image_url')
            news.content = form.cleaned_data.get('content')
            news.tag = form.cleaned_data.get('tag')
            news.save()
            return to_json_data(errmsg='文章更新成功！')
        else:
            error_msg_list = []
            for item in form.errors.get_json_data().values():
                error_msg_list.append(item[0].get('message'))
            error_msg_str = '/'.join(error_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=error_msg_str)

class HotNewsView(PermissionRequiredMixin, View):
    '''
    hot news views
    '''
    permission_required = ('news.view_hotnews',)
    raise_exception = True

    def get(self, request):
        hot_news = models.HotNews.objects.select_related('news__tag').only('news_id', 'news__title', 'news__tag__name',
                                                                           'priority').filter(is_delete=False).order_by(
            'priority', '-news__clicks')[0:SHOW_HOTNEWS_COUNT]
        return render(request, 'admin/news/news_hot.html', locals())

class HotNewsEditView(PermissionRequiredMixin, View):
    '''
    hot news edit and delete
    route:/admin/hotnews/<int:hotnews_id>
    '''
    permission_required = ('news.change_hotnews', 'news.delete_hotnews')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(HotNewsEditView, self).handle_no_permission()

    def delete(self, request, hotnews_id):
        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id, is_delete=False).first()
        if hotnews:
            hotnews.is_delete = True
            hotnews.save(update_fields=['is_delete'])
            return to_json_data(errmsg='热门新闻删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='你要删除的新闻不存在！')

    def put(self, request, hotnews_id):
        '''
        edit the hot news
        :param request:
        :param hotnews_id:
        :return:
        '''
        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id, is_delete=False).first()
        # 1、获取前端数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            priority = int(dict_data.get('priority'))
            # 2、校验
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICE]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误！')
        except Exception as e:
            logger.error('热门文章优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误!')

        if hotnews:
            if hotnews.priority == priority:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级未改变')
            else:
                # 3、对数据库中的数据更新并保存
                hotnews.priority = priority
                hotnews.save(update_fields=['priority'])
                return to_json_data(errmsg='热门文章的优先级修改成功!')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的热门文章不存在')

class AddHotNewsView(PermissionRequiredMixin, View):
    permission_required = ('news.add_hotnews', 'news.view_hotnews')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(AddHotNewsView, self).handle_no_permission()

    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).filter(
            is_delete=False).order_by('-num_news', 'update_time')
        # 获取优先级
        priority_dict = OrderedDict(models.HotNews.PRI_CHOICE)
        return render(request, 'admin/news/news_hot_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('新闻id参数错误:{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        # news=models.News.objects.only('id','title').filter(id=news_id,is_delete=False).exists()
        news = models.News.objects.filter(id=news_id).exists()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICE]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误!')
        except Exception as e:
            logger.info('热门文章优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章优先级设置错误!')

        hotnews_tuple = models.HotNews.objects.get_or_create(news_id=news_id)
        hotnews, is_created = hotnews_tuple
        hotnews.priority = priority
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg='热门文章创建成功')

class NewsByTagIdView(PermissionRequiredMixin, View):
    '''
    通过tag_id获取相应的新闻
    '''
    permission_required = ('news.add_hotnews', 'news.view_hotnews')
    raise_exception = True

    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')

    def get(self, request, tag_id):
        '''
        route:/admin/tags/<int:tag_id>/news/
        :param request:
        :param tag_id:
        :return:
        '''
        # values()转换成字典
        newes = models.News.objects.values('id', 'title').filter(tag_id=tag_id, is_delete=False)
        news_list = [i for i in newes]
        return to_json_data(data={'news': news_list})

class AddBannerView(PermissionRequiredMixin, View):
    permission_required = ('news.add_banner','news.view_banner')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(AddBannerView, self).handle_no_permission()

    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        priority_dict = OrderedDict(models.Banner.PRI_CHOICE)
        return render(request, 'admin/news/create_news_banner.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.error('获取新闻id错误{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        news = models.News.objects.only('id', 'title').filter(is_delete=False, id=news_id).exists()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.Banner.PRI_CHOICE]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='优先级设置错误')
        except Exception as e:
            logger.error('优先级设置错误{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='优先级设置错误')
            # 获取轮播图url
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url为空')
        banner_tuple = models.Banner.objects.get_or_create(news_id=news_id)
        banner, is_created = banner_tuple
        banner.priority = priority
        banner.image_url=image_url
        banner.save(update_fields=['priority','image_url'])
        return to_json_data(errmsg='新闻轮播图创建成功！')

class NewsBannerManageView(PermissionRequiredMixin, View):
    permission_required = ('news.view_banner',)
    raise_exception = True

    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')

    def get(self, request):
        banners = models.Banner.objects.only('image_url', 'id', 'priority').filter(is_delete=False)
        priority_dict = OrderedDict(models.Banner.PRI_CHOICE)
        return render(request, 'admin/news/news_banner.html', locals())

class BannerEditView(PermissionRequiredMixin, View):
    '''
    edit the news banner
    route: /admin/news/banner/<int:banner_id>/
    '''
    permission_required = ('news.change_banner', 'news.delete_banner')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(BannerEditView, self).handle_no_permission()

    def delete(self, request, banner_id):
        Banner = models.Banner.objects.only('id').filter(id=banner_id, is_delete=False).first()
        if not Banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='您要删除的轮播图不存在！')
        else:
            Banner.is_delete = True
            Banner.save(update_fields=['is_delete'])
            return to_json_data(errmsg='热门新闻删除成功！')

    def put(self, request, banner_id):
        Banner = models.Banner.objects.only('id').filter(id=banner_id, is_delete=False).first()
        if not Banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的轮播图不存在')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            priority_dict = [i for i, _ in models.Banner.PRI_CHOICE]
            if priority not in priority_dict:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        except Exception as e:
            logger.error('轮播图优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url为空')
        if Banner.priority == priority and Banner.image_url == image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url和优先级为改变')
        Banner.image_url = image_url
        Banner.priority = priority
        Banner.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg="轮播图更新成功")

class DocsManageView(PermissionRequiredMixin,View):
    permission_required = ('doc.view_doc',)
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(DocsManageView,self).handle_no_permission()
    def get(self,request):
        '''
        the index of docs manage
        :param request:
        :return: '/admin/docs_manage/
        '''
        docs=Doc.objects.only('id','title','create_time').filter(is_delete=False)
        return render(request,'admin/doc/docs_manage.html',locals())
class DocsEditView(PermissionRequiredMixin,View):
    permission_required = ('doc.view_doc','doc.delete_doc','doc.change_doc')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(DocsEditView,self).handle_no_permission()
    def get(self, request, doc_id):
        """
        获取待编辑的文档
        """
        doc = Doc.objects.only('id').filter(is_delete=False, id=doc_id).first()
        if doc:
            # doc = Doc.objects.only('id').filter(is_delete=False)
            context = {
                'doc': doc,
            }
            return render(request, 'admin/doc/docs_pub.html', context=context)
        else:
            raise Http404('您访问的新闻不存在！')
    def delete(self,request,doc_id):
        '''
        delete the docs
        :param request:
        :return:'/admin/doc/<int:doc_id>/
        '''
        doc=Doc.objects.only('id').filter(id=doc_id,is_delete=False).first()
        if not doc:
            return to_json_data(errno=Code.PARAMERR,errmsg='您要删除的文档不存在！')
        doc.is_delete=True
        doc.save(update_fields=['is_delete'])
        return to_json_data(errmsg='文档删除成功！')
    def put(self,request,doc_id):
        '''
        update the doc
        :param request:
        :param doc_id:
        :return:'/admin/doc/<int:doc_id>/
        '''
        doc = Doc.objects.only('id').filter(id=doc_id, is_delete=False).first()
        if not doc:
            return to_json_data(errno=Code.PARAMERR, errmsg='您要编辑的文档不存在！')
        json_data=request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form=forms.DocForms(data=dict_data)
        if form.is_valid():
            doc.title=form.cleaned_data.get('title')
            doc.image_url=form.cleaned_data.get('image_url')
            doc.file_url=form.cleaned_data.get('file_url')
            doc.desc=form.cleaned_data.get('desc')
            doc.save()
            return to_json_data(errmsg='文档更新成功！')
        else:
            error_msg_list=[]
            for item in form.errors.get_json_data().values():
                error_msg_list.append(item[0].get('message'))
            error_msg_str = '/'.join(error_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=error_msg_str)
class DocPubView(PermissionRequiredMixin,View):
    '''
     the doc pub views
    '''
    permission_required = ('doc.view_doc','doc.add_doc')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(DocPubView,self).handle_no_permission()
    def get(self,request):
        return render(request,'admin/doc/docs_pub.html')
    def post(self,request):
        # 1、从前端获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        # 2、校验
        form = forms.DocForms(data=dict_data)
        if form.is_valid():
            doc=form.save(commit=False)
            doc.author=request.user
            doc.save()
            return to_json_data(errmsg='文档创建成功')
        else:
            error_msg_list=[]
            for item in form.errors.get_json_data().values():
                error_msg_list.append(item[0].get('message'))
            error_msg_str = '/'.join(error_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=error_msg_str)

class CourseTagsView(PermissionRequiredMixin,View):
    permission_required = ('course.view_coursecategory','course.add_coursecategory')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(CourseTagsView,self).handle_no_permission()
    def get(self,request):
        '''
        the index of course tag
        :param request:
        :return:
        '''
        # annotate()级联查询
        tags = CourseCategory.objects.values('id', 'name').annotate(num_course=Count('course')).filter(
            is_delete=False).order_by('-num_course', '-update_time')
        return render(request,'admin/course/courses_tag.html',locals())
    def post(self,request):
        '''
        add course tag
        :param request:
        :return:
        '''
        try:
            json_data = request.body
            if not json_data:
                return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
            dict_data = json.loads(json_data.decode('utf8'))
        except Exception as e:
            logger.error('前端数据获取错误{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])
        tag_name = dict_data.get('name')
        if tag_name:
            tag_name=tag_name.strip()
            tag_tuple=CourseCategory.objects.get_or_create(name=tag_name)
            Tag,tag_boolean=tag_tuple
            return to_json_data(errmsg='课程分类创建成功') if tag_boolean else to_json_data(errno=Code.PARAMERR,errmsg='该分类已存在，请重写输入！')
        else:
            return to_json_data(errno=Code.PARAMERR,errmsg='课程标签不能为空！')

class CourseTagsEditView(PermissionRequiredMixin,View):
    permission_required = ('course.view_coursecategory','course.add_coursecategory')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(CourseTagsEditView,self).handle_no_permission()
    def delete(self,request,tag_id):
        '''
        delete the course tag
        :param request:
        :param tag_id:
        :return:'/admin/course/tag/<int:tag_id>/
        '''
        tag=CourseCategory.objects.only('id').filter(is_delete=False,id=tag_id).first()
        if not tag:
            return to_json_data(errno=Code.PARAMERR,errmsg='您删除的标签不存在')
        else:
            tag.is_delete=True
            tag.save(update_fields=['is_delete'])
            return to_json_data(errno=Code.OK, errmsg='标签删除成功')
    def put(self,request,tag_id):
        '''
        edit the course tag
        :param request:
        :param tag_id:
        :return:'/admin/course/tag/<int:tag_id>/
        '''
        tag = CourseCategory.objects.only('id').filter(is_delete=False, id=tag_id).first()
        try:
            json_data = request.body
            if not json_data:
                return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
            dict_data = json.loads(json_data.decode('utf8'))
            tag_name = dict_data.get('name')
        except Exception as e:
            logger.error('前端数据获取错误{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])
        if tag:
            tag_name=tag_name.strip()
            if tag_name:
                exist=CourseCategory.objects.only('id').filter(name=tag_name,is_delete=False).exists()
                if not exist:
                    tag.name=tag_name
                    tag.save(update_fields=['name'])
                    return to_json_data(errmsg='标签更新成功！')
                else:
                    return to_json_data(errno=Code.PARAMERR, errmsg='标签已存在！')
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg='标签名不能为空！')
        else:
            return to_json_data(errno=Code.PARAMERR,errmsg='需要更新的标签不存在')
class CourseManageView(PermissionRequiredMixin,View):
    permission_required = ('course.view_course',)
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(CourseManageView,self).handle_no_permission()
    def get(self,request):
        courses=Course.objects.only('id','title','category__name','teacher__name').filter(is_delete=False)
        return render(request,'admin/course/courses_manage.html',locals())
class PubCourseView(PermissionRequiredMixin,View):
    permission_required = ('course.view_course',)
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(PubCourseView,self).handle_no_permission()
    def get(self,request):
        categories=CourseCategory.objects.only('id','name').filter(is_delete=False)
        teachers=Teacher.objects.only('id','name').filter(is_delete=False)
        return render(request,'admin/course/courses_pub.html',locals())
    def post(self,request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form=forms.CourseForms(data=dict_data)
        if form.is_valid():
            courses_instance=form.save()
            return to_json_data(errmsg='课程发布成功')
        else:
            err_msg_list=[]
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str='/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR,errmsg=err_msg_str)

class CourseEditView(PermissionRequiredMixin,View):
    permission_required = ('course.view_course','course.change_course')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(CourseEditView,self).handle_no_permission()
    def get(self,request,course_id):
        course = Course.objects.only('id').filter(id=course_id, is_delete=False).first()
        if course:
            categories = CourseCategory.objects.only('id', 'name').filter(is_delete=False)
            teachers = Teacher.objects.only('id', 'name').filter(is_delete=False)
            context={
                'course':course,
                'categories':categories,
                'teachers':teachers
            }
            return render(request, 'admin/course/courses_pub.html', context=context)
        else:
            raise Http404('您访问的课程不存在！')
    def delete(self,request,course_id):
        '''
        delete the course function
        :param request:
        :param course_id:
        :return: '/admin/course/<int:course_id>/
        '''
        course=Course.objects.only('id').filter(id=course_id,is_delete=False).first()
        if course:
            course.is_delete=True
            course.save(update_fields=['is_delete'])
            return to_json_data(errmsg='课程删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR,errmsg='您要删除的课程不存在！')
    def put(self,request,course_id):
        '''
        edit the course function
        :param request:
        :param course_id:
        :return:'/admin/course/<int:course_id>/
        '''
        course = Course.objects.only('id').filter(id=course_id, is_delete=False).first()
        if not course:
            return to_json_data(errno=Code.PARAMERR,errmsg='需要更新的课程不存在')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form=forms.CourseForms(data=dict_data)
        if form.is_valid():
            # form.cleaned_data是返回字典类型，.items()返回的是元祖类型
            for attr,value in form.cleaned_data.items():
                setattr(course,attr,value)
            course.save()
            return to_json_data(errmsg='课程更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)  # 拼接错误信息为一个字符串
class AddGroupView(PermissionRequiredMixin,View):
    '''
    create group
    '''
    permission_required = ('auth.view_group','auth.add_group')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(AddGroupView,self).handle_no_permission()
    def get(self,request):
        permissions = Permission.objects.only('id').all()
        return render(request, 'admin/users/groups_add.html', locals())
    def post(self,request):
        '''
        create group and add permission
        :return: '/admin/group_add/'
        '''
        # 1、获取前端数据
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        # 校验
        group_name=dict_data.get('group_name','').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR,errmsg='组名称不能为空！')
        # 判断组名是否已经存在
        group,is_create=Group.objects.get_or_create(name=group_name)
        if not is_create:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名已存在，请重新输入')
        group_permissions=dict_data.get('group_permissions')
        # 判断权限参数是否为空
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')
        try:
            # 集合推倒式获取用户选择的权限，集合有去重的功能
            permissions_set=set(int(i) for i in group_permissions)
        except Exception as e:
            logger.error('权限参数异常{}'.format(e))
            return to_json_data(errno=Code.PARAMERR,errmsg='权限参数异常')
        # 获取数据库中所有的权限
        all_permissions_set=set(i.id for i in Permission.objects.only('id'))
        #issubset() 方法用于判断集合的所有元素是否都包含在指定集合中，如果是则返回 True，否则返回 False。
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR,errmsg='有不存在的权限参数')
        for perm_id in permissions_set:
            # 获取id=perm_id的权限
            p=Permission.objects.get(id=perm_id)
            group.permissions.add(p)
        group.save()
        return to_json_data(errmsg='组创建成功！')

class UserGroupManageView(PermissionRequiredMixin,View):
    permission_required = ('auth.view_group','auth.add_group')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(UserGroupManageView,self).handle_no_permission()
    def get(self,request):
        groups=Group.objects.values('id','name').annotate(num_users=Count('user')).order_by('-num_users','id')
        return render(request,'admin/users/groups_manage.html',locals())
class GroupEditView(PermissionRequiredMixin,View):
    permission_required = ('auth.view_group','auth.delete_group','auth.change_view')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(GroupEditView,self).handle_no_permission()
    def get(self,request,group_id):
        '''
        get to group_id
        :param request:
        :param group_id:
        :return:'/admin/group/<int:group_id>/
        '''
        group=Group.objects.filter(id=group_id).first()
        if group:
            permissions=Permission.objects.only('id').all()
            return render(request,'admin/users/groups_add.html',locals())
        else:
            raise Http404('需要更新的组不存在！')
    def delete(self,request,group_id):
        '''
        delete the group function
        :param request:
        :param group_id:
        :return: '/admin/group/<int:group_id>/'
        '''
        group=Group.objects.filter(id=group_id).first()
        if group:
            group.permissions.clear()  # 清空权限
            group.delete()
            return to_json_data(errmsg='用户组删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的用户组不存在")
    def put(self,request,group_id):
        '''
        edit the group and group permissions
        :param request:
        :param group_id:
        :return:
        '''
        group = Group.objects.only('id').filter(id=group_id).first()
        if not group:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要更新的的用户组不存在")
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        group_name=dict_data.get('group_name','').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空')
        if group_name != group.name and Group.objects.filter(name=group_name).exists():
            return to_json_data(errno=Code.PARAMERR,errmsg='组名已存在')
        group_permissions=dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')
        try:
            permissions_set=set(int(i) for i in group_permissions)
        except Exception as e:
            logger.error('权限参数异常{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常')
        all_permissions_set=set(i.id for i in Permission.objects.only('id'))
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数')
        # 获取当前用户组下的权限信息
        exist_permission_set=set(i.id for i in group.permissions.all())
        if group_name ==group.name and permissions_set == exist_permission_set:
            return to_json_data(errno=Code.PARAMERR,errmsg='用户组信息未修改')

        for perm_id in permissions_set:
            p=Permission.objects.get(id=perm_id)
            group.permissions.add(p)
        group.name = group_name
        group.save()
        return to_json_data(errmsg='组更新成功！')


class UserManageView(PermissionRequiredMixin,View):
    permission_required = ('users.view_user',)
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(UserManageView,self).handle_no_permission()
    def get(self,request):
        '''
        the index of user table
        :param request:
        :return: '/admin/user_manage/'
        '''
        users=User.objects.only('username','is_staff','is_superuser','groups__name').filter(is_active=True)
        return render(request,'admin/users/users_manage.html',locals())
class UserEditView(PermissionRequiredMixin,View):
    permission_required = ('users.view_user','users.change_user','users.delete_user')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower!='get':
            return to_json_data(errno=Code.ROLEERR,errmsg='没有操作权限')
        else:
            return super(UserEditView,self).handle_no_permission()
    def get(self,request,user_id):
        user_instance=User.objects.filter(id=user_id,is_active=True).first()
        if user_instance:
            groups=Group.objects.only('name').all()
            return render(request,'admin/users/users_edit.html',locals())
        else:
            raise Http404('需要更新的用户不存在！')
    def delete(self,request,user_id):
        '''
        delete the user function
        :param request:
        :param user_id:
        :return: '/admin/user/<int:user_id>/'
        '''
        user_instance=User.objects.only('id').filter(id=user_id,is_active=True).first()
        if user_instance:
            user_instance.is_active=False
            user_instance.groups.clear() #清除用户组
            user_instance.user_permissions.clear() #清除用户权限
            user_instance.save()
            return to_json_data(errmsg='用户删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR,errmsg='您删除的用户不存在！')
    def put(self,request,user_id):
        '''
        edit the user function
        :param request:
        :param user_id:
        :return:
        '''
        user_instance = User.objects.only('id').filter(id=user_id, is_active=True).first()
        if not user_instance:
            return to_json_data(errno=Code.PARAMERR, errmsg='您要更新的用户不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            groups=dict_data.get('groups')  # 取出用户组列表

            is_active=int(dict_data.get('is_active'))
            is_superuser=int(dict_data.get('is_superuser'))
            is_staff=int(dict_data.get('is_staff'))
            param=[is_active,is_staff,is_superuser]
            if not all(p in (0,1) for p in param):
                return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        except Exception as e:
            logger.error('从前端获取参数错误:{}'.format(e))
            return to_json_data(errno=Code.PARAMERR,errmsg='参数错误')
        try:
            group_set=set(int(i) for i in groups) if groups else set()
        except Exception as e:
            logger.info('传的用户组参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='用户组参数异常')

        all_group_set=set(i.id for i in Group.objects.only('id'))
        if not group_set.issubset(all_group_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的用户组参数')
        # exist_group_set=set(i.id for i in user_instance.groups.all())
        # print('111111111111111',exist_group_set)
        # if user_instance.is_active ==is_active and user_instance.is_staff ==is_staff and user_instance.is_superuser ==is_superuser and group_set==exist_group_set:
        #     return to_json_data(errno=Code.PARAMERR, errmsg='用户信息未修改')
        # models.Tb1.objects.filter(id__in=[11, 22, 33])   # 获取id等于11、22、33的数据
        gs=Group.objects.filter(id__in=group_set)
        print('111111111')
        print(gs)
        print('111111111')
        user_instance.groups.clear()
        user_instance.groups.set(gs)

        user_instance.is_active=bool(is_active)
        user_instance.is_superuser=bool(is_superuser)
        user_instance.is_staff=bool(is_staff)
        user_instance.save()
        return to_json_data(errmsg='用户信息更新成功！')


















class UploadFdfs(PermissionRequiredMixin, View):
    '''
    upload image file to fdfs server
    '''
    permission_required = ('news.add_news',)
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有上传图片的权限')

    def post(self, request):
        # 从前端获取图片文件对象
        image_file = request.FILES.get('image_file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取图片失败！')
        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif','image/jpg'):
            logger.info('文件格式错误！')
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非图片文件')
        # 获取图片文件后缀名 jpg
        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名错误：{}'.format(e))
            image_ext_name = 'jpg'
        try:
            # filename.read()读取文件内容，image_ext_name获取文件后缀名
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FASTDFS服务器失败')
                return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传到服务器失败')
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功！')

class QiqiuToken(View):
    '''
    image upload to qiniu
    '''

    def get(self, request):
        access_key = settings.QINIU_ACCESS_KEY
        secret_key = settings.QINIU_SECRET_KEY

        q = qiniu.Auth(access_key, secret_key)

        bucket_name = settings.QINIU_BUCKET_NAME
        token = q.upload_token(bucket_name)
        # 这里返回一个原声的json数据，不要用自定义的to_json_data，否则可能会有问题。
        return JsonResponse({'uptoken': token})
class DocsUploadFile(PermissionRequiredMixin, View):
    '''
    upload image file to fdfs server
    '''
    permission_required = ('doc.add_doc',)
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有上传图片的权限')

    def post(self, request):
        # 从前端获取图片文件对象
        text_file = request.FILES.get('text_file')
        if not text_file:
            logger.info('从前端获取文件失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取文件失败！')
        if text_file.content_type not in ('application/msword', 'application/octet-stream', 'application/pdf',
                                          'application/zip', 'text/plain', 'application/x-rar'):
            logger.info('文件格式错误！')
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非文本文件')
        # 获取图片文件后缀名 jpg
        try:
            text_ext_name = text_file.name.split('.')[-1]
        except Exception as e:
            logger.info('文本拓展名错误：{}'.format(e))
            text_ext_name = 'pdf'
        try:
            # filename.read()读取文件内容，image_ext_name获取文件后缀名
            upload_res = FDFS_Client.upload_by_buffer(text_file.read(), file_ext_name=text_ext_name)
        except Exception as e:
            logger.error('文档上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文档上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('文档上传到FASTDFS服务器失败')
                return to_json_data(errno=Code.UNKOWNERR, errmsg='文档上传到服务器失败')
            else:
                text_name = upload_res.get('Remote file_id')
                text_url = settings.FASTDFS_SERVER_DOMAIN + text_name
                return to_json_data(data={'text_url': text_url}, errmsg='文档上传成功！')
