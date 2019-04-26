from rest_framework import serializers
from . import models
from apps.users.serializers import UserSerializers

# 创建TAG序列化
class TagSerializers(serializers.ModelSerializer):
    class Meta:
        model=models.Tag
        fields=('id','name')

# djangorestframwork可以更好的将django模型转换为json对象，以方便ajax使用。
# 创建序列化
class NewsSerializers(serializers.ModelSerializer):
    # 当访问tag这个字段时，会自动去访问NewsSerializers()这个函数
    tag=TagSerializers()
    author=UserSerializers()
    class Meta:
        model=models.News
        # 其中‘tag’,'author',是通过外键引入的，需要分别再去写一个序列化，告诉以后当需要category字段的时候需要提取哪些字段。
        fields=('id','title','digest','image_url','create_time','tag','author','update_time','is_delete')

class CommentSerializers1(serializers.ModelSerializer):
    author=UserSerializers()
    news=NewsSerializers()
    class Meta:
        model=models.Comment
        fields="__all__"
class CommentSerializers(serializers.ModelSerializer):
    author=UserSerializers()
    news=NewsSerializers()
    sub_comment=CommentSerializers1(many=True)
    class Meta:
        model=models.Comment
        fields="__all__"