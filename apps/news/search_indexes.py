from haystack import indexes
from .models import News

# 模型名+Index()固定写法
class NewsIndex(indexes.SearchIndex, indexes.Indexable):
    """
    News索引数据模型类
    """
    # text必须写，固定写法，不要更改，是elasticsearch引擎框架与django中haystack交互的桥梁。
    text = indexes.CharField(document=True, use_template=True)
    id = indexes.IntegerField(model_attr='id')
    title = indexes.CharField(model_attr='title')
    digest = indexes.CharField(model_attr='digest')
    content = indexes.CharField(model_attr='content')
    image_url = indexes.CharField(model_attr='image_url')
    # comments = indexes.IntegerField(model_attr='comments')

    def get_model(self):
        """返回建立索引的模型类
        """
        return News

    def index_queryset(self, using=None):
        """返回要建立索引的数据查询集
        """
        # 只搜索逻辑未删除的内容。
        return self.get_model().objects.filter(is_delete=False, tag_id__in=[1,2,3,4,5])