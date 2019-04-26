from django.db import models


from utils.models import ModelBase
from django.core.validators import MinLengthValidator,MaxLengthValidator

# Create your models here.

class Doc(ModelBase):
    '''
    create doc model
    '''
    title=models.CharField(max_length=150,verbose_name="文档标题",help_text="文档标题",validators=[MinLengthValidator(1),])
    file_url=models.URLField(verbose_name="文件url",validators=[MinLengthValidator(1), ],help_text="文件url",)
    desc=models.TextField(verbose_name="文档描述",help_text="文档描述",validators=[MinLengthValidator(1),MaxLengthValidator(200),])
    image_url=models.URLField(validators=[MinLengthValidator(1), ],default="",verbose_name="图片url", help_text="图片url")
    author=models.ForeignKey('users.User',on_delete=models.SET_NULL,null=True)

    class Meta:
        db_table="tb_doc"
        verbose_name="文档"
        verbose_name_plural=verbose_name

    def __str__(self):
        return self.title