import logging
import re

from django import forms
from django.contrib.auth import login,logout
from django.core.validators import RegexValidator
from django_redis import get_redis_connection
from django.db.models import Q

from apps.verification.constants import SMS_CODE_NUMS
from .models import User

class RegisterForm(forms.Form):
    '''
    Verfily users register from
    '''
    username=forms.CharField(label='用户名',min_length=5,max_length=20,error_messages={
        "min_length": "用户名长度要大于5",
        "max_length": "用户名长度要小于20",
        "required": "用户名不能为空"
    })
    password=forms.CharField(label='密码', max_length=20, min_length=6,error_messages={
        "min_length": "密码长度要大于6",
        "max_length": "密码长度要小于20",
        "required": "密码不能为空"
    })
    password_repeat=forms.CharField(label='重复密码', max_length=20, min_length=6,error_messages={
        "min_length": "密码长度要大于6",
        "max_length": "密码长度要小于20",
        "required": "密码不能为空"
    })
    telephone=forms.CharField(label='手机号码',max_length=11,min_length=11,error_messages={
        "min_length":"手机号码必须为11位",
        'max_length': '手机号码必须为11位',
        'required': '手机号码不能为空',
    })
    sms_code=forms.CharField(label='短信验证码',min_length=SMS_CODE_NUMS,max_length=SMS_CODE_NUMS,error_messages={
        "min_length": "短信验证码长度有误",
        "max_length": "短信验证码长度有误",
        "required": "短信验证码不能为空"
    })
    def clean_username(self):
        '''
        check username
        :return:
        '''
        username=self.cleaned_data.get('username')
        exists=User.objects.filter(username=username).exists()
        if exists:
            raise forms.ValidationError('该用户名已注册，请重新输入')
        return username

    def clean_telephone(self):
        '''
        check telephone
        :return:
        '''
        tel=self.cleaned_data.get('telephone')
        if not re.match(r"^1[3-9]\d{9}$",tel):
            raise forms.ValidationError('手机号码格式不正确')
        exists=User.objects.filter(telephone=tel).exists()
        if exists:
            raise forms.ValidationError('该手机号已注册，请重新输入')
        return tel
    def clean(self):
        '''
        check whether the two password are the same ,and check whether the sms_code is correct
        :param self:
        :return:
        '''
        # 1 获取数据
        cleaned_data=super().clean()
        passwd=cleaned_data.get('password')
        password_repeat=cleaned_data.get('password_repeat')
        tel = cleaned_data.get('telephone')
        sms_code = cleaned_data.get('sms_code')
        # 2 判断两次密码是否一致
        if passwd != password_repeat:
            raise forms.ValidationError('两次密码不一致，请重新输入！')
        # 建立redis数据库
        redis_conn=get_redis_connection(alias='ImgCaptcha')
        # 创建一把短信验证码发送记录钥匙
        sms_flag_ft='sms_{}'.format(tel).encode('utf8')
        sever_sms_code=redis_conn.get(sms_flag_ft)
        # 判断短信验证码是否存在以及是否与前端输入的一致.
        if (not sever_sms_code) or (sms_code != sever_sms_code.decode('utf-8')):
            raise forms.ValidationError('短信验证码错误')

class LoginForm(forms.Form):
    '''
    login form data
    '''
    user_account=forms.CharField()
    password=forms.CharField(label='密码',min_length=6,max_length=20,error_messages={
        'required':'必须填入密码',
        'min_length':'密码长度不能少于6位',
        'max_length':'密码长度不能大于20位',
    })
    remember=forms.BooleanField(required=False)
    # 因为设置会话时间需要用到request，而request是view视图中的方法，所以得从view视图中传到form表单验证中
    # LoginForm(data=dict_data,request=request)，因为用的是request=request，所以会被**kwarg接收，如果直接传的是的request，就是会*args接收，但是建议使用request=request。
    def __init__(self,*args,**kwargs):
        '''
        recive request form views
        :param args:
        :param kwargs:
        '''
        self.request=kwargs.pop('request',None)
        super().__init__(*args,**kwargs)

    def clean_user_account(self):
        '''
        check user_account
        :return:
        '''
        user_account=self.cleaned_data.get('user_account')
        if not user_account:
            raise forms.ValidationError('用户账号不能为空！')
        if not re.match(r"^1[3-9]\d{9}$",user_account) and (len(user_account)<5 or len(user_account)>20):
            raise forms.ValidationError("用户账号格式不正确，请重新输入")
        return user_account
    def clean(self):
        '''
        check telephone ,username ,password,remember
        :return:
        '''
        cleaned_data=super().clean()
        user_info=cleaned_data.get('user_account')
        pwd=cleaned_data.get('password')
        remember=cleaned_data.get('remember')

        user_query=User.objects.filter(Q(telephone=user_info) | Q(username=user_info))

        if user_query:
            # 将第一个用户取出
            user=user_query.first()
            # check_password是user自带的一个方法，可以自动检验前端获取的密码加密是否和数据库中加密的密码是否相等，相等则返回True,否则返回False
            if user.check_password(pwd):
                # 3、是否将用户信息设置到回话中
                if remember:
                    # 如果是None则表示默认两周后到期，若是0则表示关闭浏览器则自动消失
                    self.request.session.set_expiry(None)
                else:
                    self.request.session.set_expiry(0)
                login(self.request,user)
            else:
                raise forms.ValidationError('密码有误请重新输入！')
        else:
            raise forms.ValidationError('用户账号格式不正确，请重新输入')











