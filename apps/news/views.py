import logging
import json

from django.shortcuts import render
from django.views import View
from django.http import Http404,HttpResponse
from django.core.paginator import Paginator,EmptyPage,PageNotAnInteger
from haystack.views import SearchView as _SearchView
from django.conf import settings
# 可以对url进行编辑
from urllib import parse

from . import models,constants,serializers
from utils.json_fun import to_json_data
from utils.res_code import Code,error_map


# Create your views here.
logger=logging.getLogger('django')

class IndexView(View):
    '''
        the index of the web
    '''
    def get(self,request):
        # only(),表示只提取某些字段，difer()表示排除某些字段，可以提升性能
        tags=models.Tag.objects.only('id','name').filter(is_delete=False)
        newes=models.News.objects.select_related('tag','author').only('title','digest','image_url','author__username','tag__name','update_time').filter(is_delete=False)
        banners=models.Banner.objects.select_related('news').only('image_url','news__id','news__title').filter(is_delete=False).order_by('priority','-update_time','-id')[0:constants.ONE_PAGE__NEWS_COUNT]
        hot_news=models.HotNews.objects.select_related('news').only('news__image_url','news__title','news__id').filter(is_delete=False).order_by('priority','-update_time','-id')[:3]
        return render(request,'news/index.html',locals())

# 1、创建类视图
class NewslistView(View):
    def get(self,request):
        # 2、数据校验，是否为空，是否为整数。
        try:
            tag_id=int(request.GET.get('tag_id',0))
        except Exception as e:
            logger.error('新闻标签错误：{}'.format(e))
            tag_id=0
        try:
            page=int(request.GET.get('page',1))
        except Exception as e:
            logger.error('当前页错误：{}'.format(e))
            page=1
        # 3、获取新闻列表数据
        newes_query=models.News.objects.select_related('tag','author').only('title','digest','image_url','author__username','tag__name','update_time')
        # 如果标签分类存在则返回news_query.filter(is_delete=False,tag_id=tag_id)，如果不存在则返回后者。
        newes=newes_query.filter(is_delete=False,tag_id=tag_id) or newes_query.filter(is_delete=False)
        # 创建对象
        paginator = Paginator(newes, constants.ONE_PAGE__NEWS_COUNT)
        # 某一页的数据
        try:
            pag_objects = paginator.page(page)
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logging.info("用户访问的页数大于总页数。")
            pag_objects = paginator.page(paginator.num_pages)
        # 4、序列化
        # newes_info_list=[]
        # for n in pag_objects:
        #     newes_info_list.append({
        #         'id':n.id,
        #         'title':n.title,
        #         'digest':n.digest,
        #         'image_url':n.image_url,
        #         'author':n.author.username,
        #         'tag_name':n.tag.name,
        #         'update_time':n.update_time.strftime('%Y-%m-%d %H:%m:%S')
        #     })
        serializer=serializers.NewsSerializers(pag_objects,many=True)
        data={
            'total_pages':paginator.num_pages,
            'newes':serializer.data
            # 'newes':newes_info_list
        }
        # 5、返回前端
        return to_json_data(data=data)

class NewsDetailView(View):
    '''
    create news detail view
    route:newsdetail/news_id
    '''
    def get(self,request,news_id):
        news=models.News.objects.order_by('tag','author').only('id','title','author__username','tag__name','update_time','content')\
            .filter(is_delete=False,id=news_id).first()
        if news:
            comments=models.Comment.objects.select_related('author','parent')\
                .only('content','update_time','author__username','parent__author__username','parent__update_time','parent__content').\
                filter(is_delete=False,news_id=news_id)
            comment_lists=[]
            for comment in comments:
                comment_lists.append(comment.to_dict_data())
            # comment_data=serializers.CommentSerializers(comments,many=True)
            # comment_lists=comment_data.data
            return render(request,'news/news_detail.html',locals())
        else:
            raise Http404('新闻{}，不存在'.format(news_id))

class CommentView(View):
    def post(self,reqeust,news_id):
        '''
        create news commenr view
        route:/<news_id>/comment/
        :param reqeust:
        :param news_id:
        :return:
        '''
        # 判断用户是否登录以及新闻是否存在，只有新闻存在以及用户登录了才可进行下面的操作
        if not reqeust.user.is_authenticated:
            return to_json_data(errno=Code.SESSIONERR,errmsg=error_map[Code.SESSIONERR])
        if not models.News.objects.only('id').filter(is_delete=False,id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR,errmsg='新闻不存在')
        # 获取前端数据
        try:
            json_data=reqeust.body
            if not json_data:
                return to_json_data(errno=Code.PARAMERR,errmsg=error_map[Code.PARAMERR])
            dict_data=json.loads(json_data.decode('utf8'))
        except Exception as e:
            logging.info('错误信息：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR,errmsg=error_map[Code.UNKOWNERR])
        # 数据验证
        content=dict_data.get('content')
        if not content:
            return to_json_data(errno=Code.PARAMERR,errmsg='评论为空，请重新输入！')
        # 或取到的是一个字符串格式
        parent_id=dict_data.get('parent_id')
        try:
            if parent_id:
                parent_id=int(parent_id)
                exist=models.Comment.objects.only('id').filter(is_delete=False,id=parent_id,news_id=news_id).exists()
                if not exist:
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        except  Exception as e:
            logger.info('前端传来的parent_id有异常:{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR,errmsg=error_map[Code.UNKOWNERR])

        news_commet=models.Comment()
        news_commet.content=content
        news_commet.author=reqeust.user
        news_commet.news_id=news_id
        # 加个判断，只有当parent_id存在时，news_commet.parent_id=parent_id才成立。
        news_commet.parent_id=parent_id if parent_id else None
        news_commet.save()
        return to_json_data(data=news_commet.to_dict_data())

class SearchView(_SearchView):
    # 模板文件
    template='news/search.html'
    # 重写create_response方法，如果请求参数q为空，返回模型News的热门新闻数据，否则根据参数q搜索相关数据。
    def create_response(self):
        kw=self.request.GET.get('q','')
        if not kw:
            show_all=True
            hot_news=models.HotNews.objects.select_related('news').only('news__title','news__image_url','news_id','news__author__username','news__update_time').\
                filter(is_delete=False).order_by('priority','-news__clicks')
            # paginator不能改动
            paginator=Paginator(hot_news,settings.HAYSTACK_SEARCH_RESULTS_PER_PAGE)
            try:
                # page不能改动
                page = int(self.request.GET.get('page', 1))
                page=paginator.page(page)
            except PageNotAnInteger:
                logging.info('输入的值不符合规范！')
                page=paginator.page(1)
            except EmptyPage:
                logging.info("用户访问的页数大于总页数。")
                page=paginator.page(paginator.num_pages)
            except Exception as e:
                page = paginator.page(1)
            return render(self.request,self.template,locals())
        else:
            show_all=False
            # 调用父类的create_response()方法
            qs=super(SearchView,self).create_response()
            return qs


















