import json

from django.shortcuts import render
from django.views import View
from django.contrib.auth import login

from utils.json_fun import to_json_data
from utils.res_code import Code,error_map
from .forms import RegisterForm
from .models import User

# Create your views here.

def Login(request):
    '''
    用户登录页面
    :param request:
    :return:
    '''
    return render(request,'users/login.html')

# 1 创建一个注册类
class RegisterView(View):
    # 2 创建get 方法
    def get(self,request):
        '''
        get method
        :param request:
        :return:
        '''
        return render(request,'users/register.html')
    # 3 创建post方法
    def post(self,request):
        '''
        handle post request ,include verfily  form datas
        :param request:
        :return:
        '''
    # 4 获取前端数据
        json_data = request.body
        # json.loads(a),将a转换成字典格式
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        form=RegisterForm(data=dict_data)
        if form.is_valid():
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password')
            telephone=form.cleaned_data.get('telephone')
            user=User.objects.create_user(username=username,password=password,telephone=telephone)
            login(request,user)
            return to_json_data('注册成功!')
        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)










