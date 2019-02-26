import logging
import re

from django import forms
from django.core.validators import RegexValidator
from django_redis import get_redis_connection

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
    repeat_password=forms.CharField(label='重复密码', max_length=20, min_length=6,error_messages={
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
        exists=User.objects.filter(username==username).exists()
        if exists:
            raise forms.ValidationError('该用户名已注册，请重新输入')
        return username

    def clean_telephone(self):
        '''
        check telephone
        :return:
        '''
        telephone=self.cleaned_data.get('telephone')
        if not re.match(r"^1[3-9]]\d{9}$",telephone):
            raise forms.ValidationError('手机格式不正确')

        exists=User.objects.filter(telephone==telephone).exists()
        if exists:
            raise forms.ValidationError('该手机号已注册，请重新输入')
        return telephone
    def clean(self):
        '''
        check whether the two password are the same ,and check whether the sms_code is correct
        :param self:
        :return:
        '''
        # 1 获取数据
        clean_data=super().cleaned()
        passwd=clean_data.get('password')
        repeat_passwd=clean_data.get('repeat_password')
        tel = clean_data.get('telephone')
        sms_code = clean_data.get('sms_code')
        # 2 判断两次密码是否一致
        if passwd != repeat_passwd:
            raise forms.ValidationError('两次密码不一致，请重新输入！')
        # 建立redis数据库
        redis_conn=get_redis_connection(alias='ImgCaptcha')
        # 创建一把短信验证码发送记录钥匙
        sms_flag_ft='img_{}'.format(tel).encode('utf8')
        sever_sms_code=redis_conn.get(sms_flag_ft)
        # 判断短信验证码是否存在以及是否与前端输入的一致.
        if (not sever_sms_code) or (sms_code !=sever_sms_code):
            raise forms.ValidationError('短信验证码错误')








