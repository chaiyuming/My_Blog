import logging

from django import forms
from django.core.validators import RegexValidator
from django_redis import get_redis_connection

from apps.users.models import User

# 导入日志器
logger = logging.getLogger('django')


# 创建手机号的正则校验器
mobile_validator = RegexValidator(r"^1[3-9]\d{9}$", "手机号码格式不正确")
class SmsCaptchaForm(forms.Form):
    telephone=forms.CharField(max_length=11,min_length=11,validators=[mobile_validator,],error_messages={
        "min_length":"手机号码必须为11位",
        'max_length': '手机号码必须为11位',
        'required': '手机号码不能为空',
    })
    image_code_id=forms.UUIDField(error_messages={
        'required': '图片UUID不能为空',
    })
    text=forms.CharField(max_length=4,min_length=4,error_messages={
        "min_length":"请输入四位数字的图像验证码",
        "max_length":"请输入四位数字的图像验证码",
        "required":"请输入图形验证码",
    })

    def clean_telephone(self):
        '''
        对单个字段进行校验:clean+'_'+'校验的字段'是固定写法
        校验手机号是否存在；
        :return:
        '''
        tel=self.cleaned_data.get('telephone')
        exist = User.objects.filter(telephone=tel).exists()
        if exist:
            raise forms.ValidationError('该手机号已经注册！')
        return tel

    def clean(self):
        '''
        clean可以对多个字段进行联合校验
        :return:
        '''
        cleaned_data=super().clean()
        image_code_id=cleaned_data.get('image_code_id')
        text=cleaned_data.get('text')
        telephone=cleaned_data.get('telephone')

        # 1、获取图片验证码
        try:
            con_redis=get_redis_connection(alias='ImgCaptcha')
        except Exception as e:
            logger.error("redis数据库异常[%s]"%e)
            raise forms.ValidationError("未知错误，请重试！")
        # 创建一把图形验证码发送记录钥匙
        img_flag_fmt='img_{}'.format(image_code_id).encode('utf8')
        # 取出图片验证码
        sever_img_code_orign=con_redis.get(img_flag_fmt)
        sever_img_code=sever_img_code_orign.decode('utf8') if sever_img_code_orign else None
        # 2、判断用户输入的图片验证码是否正确
        if (not sever_img_code) or (text != sever_img_code.lower()):
            raise forms.ValidationError('图形验证码验证失败！')
        #3、判断在60s内是否有发送记录
        # 创建一把短信验证码发送记录钥匙,sms_flag_fmt是一个字节格式的数据
        sms_flag_fmt='sms_{}'.format(telephone).encode('utf8')
        sever_sms_code=con_redis.get(sms_flag_fmt)
        if sever_sms_code:
            raise  forms.ValidationError('获取短信验证码过于频繁，请稍后再试！')





