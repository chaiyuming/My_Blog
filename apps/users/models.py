from django.db import models
from django.contrib.auth.models import AbstractBaseUser,AbstractUser,UserManager as _UserManager,User

# Create your models here.
class UserManager(_UserManager):
    '''
    重写UserManager中的
    '''
    def create_superuser(self, username, password, email=None, **extra_fields):
        super().create_superuser(username=username,password=password,email=email,**extra_fields)

class User(AbstractUser):
    '''
    add mobile,email_active fields to Users models.
    '''
    telephone=models.CharField(max_length=11,unique=True,help_text='手机号码',verbose_name='手机号码',
                               error_messages={
                                   'unique':'此手机号码已经注册'
                               })
    email_active=models.BooleanField(default=False,verbose_name='邮箱验证状态')


    # 这个属性使用来，以后在命令行中使用createsuperuser命令的时候会让你输入的字段
    REQUIRED_FIELDS = ['telephone']
    objects = UserManager()

    class Meta:
        db_table='tb_users'
        # admin站点显示
        verbose_name='用户'
        # 复数
        verbose_name_plural=verbose_name
    def get_groups_name(self):
        groups_name_list=[i.name for i in self.groups.all()]
        return '|'.join(groups_name_list)
    def __str__(self):
        return self.username


