from django.db import models
from utils.models import ModelBase
# 最小长度校验器，因为在刚开始没有添加min_length这个属性，所以需要添加一个校验器来校验，因为在form表单error_message中，需要填写min_length。
from django.core.validators import MinLengthValidator


# Create your models here.

class Tag(ModelBase):
    '''
    the category of news
    '''
    name=models.CharField(max_length=100,verbose_name='标签名',help_text='标签名')

    class Meta:
        ordering=['-update_time','-id']
        db_table='tb_tag'
        verbose_name="新闻标签"
        verbose_name_plural=verbose_name
    def __str__(self):
        return self.name

class News(ModelBase):
    '''
    新闻表
    '''
    title=models.CharField(max_length=100,validators=[MinLengthValidator(1),],verbose_name='标题',help_text='标题')
    digest=models.CharField(max_length=100,validators=[MinLengthValidator(1),],verbose_name='摘要',help_text='摘要')
    content=models.TextField(verbose_name='内容',help_text='内容')
    clicks=models.IntegerField(default=0,verbose_name='点击量',help_text='点击量')
    image_url=models.URLField(default="",verbose_name='图片URL',help_text='图片URL')

    tag=models.ForeignKey('Tag',on_delete=models.SET_NULL,null=True)
    author=models.ForeignKey('users.User',on_delete=models.SET_NULL,null=True)

    class Meta:
        ordering=['-update_time','-id']
        db_table='tb_news'
        verbose_name='新闻'
        verbose_name_plural=verbose_name
    def __str__(self):
        return self.title

class Comment(ModelBase):
    content=models.TextField(verbose_name="内容",help_text='内容')
    author=models.ForeignKey('users.User',on_delete=models.CASCADE,help_text='作者',verbose_name='作者')
    news=models.ForeignKey('News',on_delete=models.CASCADE)
    parent=models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True,related_name='sub_comment')

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_comments"  # 指明数据库表名
        verbose_name = "评论"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def to_dict_data(self):
        comment_dict = {
            'news_id': self.news.id,
            'content_id': self.id,
            'content': self.content,
            'author': self.author.username,
            'update_time': self.update_time.strftime('%Y年%m月%d日 %H:%M'),
            'parent': self.parent.to_dict_data() if self.parent else None,
        }

        return comment_dict
    def __str__(self):
        return "<评论{}>".format(self.id)
class HotNews(ModelBase):
    '''
    the hot news
    '''
    PRI_CHOICE=[
        (1,'第一级'),
        (2,'第二级'),
        (3,'第三级'),
    ]
    # OneToOneField()表示一对一
    news=models.OneToOneField('News',on_delete=models.CASCADE)
    priority=models.IntegerField(choices=PRI_CHOICE,default=3,verbose_name='优先级',help_text='优先级')

    class Meta:
        ordering=['-update_time','-id']
        db_table='tb_hotnews'
        verbose_name='热门新闻'
        verbose_name_plural=verbose_name
    def __str__(self):
        return "<热门新闻{}>".format(self.id)
class Banner(ModelBase):
    '''
    the banner of the index of news
    '''
    PRI_CHOICE=[
        (1,'第一级'),
        (2,'第二级'),
        (3,'第三级'),
        (4,'第四级'),
        (5,'第五级'),
        (6,'第六级'),
    ]
    image_url=models.URLField(verbose_name='图片URL',help_text='图片URL')
    priority = models.IntegerField(choices=PRI_CHOICE,default=6,verbose_name='优先级', help_text='优先级')
    news = models.OneToOneField('News', on_delete=models.CASCADE)

    class Meta:
        ordering=['priority','-update_time','-id']
        db_table='tb_banner'
        verbose_name='轮播图'
        verbose_name_plural=verbose_name

    def __str__(self):
        return "<轮播图{}>".format(self.id)






