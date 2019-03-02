import json
import logging

from django.shortcuts import render,redirect,reverse
from django.views import View
from django.contrib.auth import login,logout

from utils.json_fun import to_json_data
from utils.res_code import Code,error_map
from .forms import RegisterForm,LoginForm
from .models import User

# Create your views here.
# 导入日志器
logger = logging.getLogger('django')

# 1 创建一个注册类
class RegisterView(View):
    '''
    user register
    '''
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
        try:
            json_data = request.body
            # json.loads(a),将a转换成字典格式
            if not json_data:
                return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
            dict_data = json.loads(json_data.decode('utf8'))
        except Exception as e:
            logging.info("错误信息，\n{}".format(e))
            return to_json_data(errno=Code.UNKOWNERR,errmsg=error_map[Code.UNKOWNERR])
        # 5\校验数据
        form=RegisterForm(data=dict_data)
        if form.is_valid():
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password')
            telephone=form.cleaned_data.get('telephone')
            user=User.objects.create_user(username=username,password=password,telephone=telephone)
            login(request,user)
            return to_json_data(errno=Code.OK,errmsg='注册成功!')
        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)
#1、 创建类
class LoginView(View):
    '''
    user login view
    '''
    def get(self,request):
        return render(request, 'users/login.html')
    def post(self,request):
        try:
            # 2、获取前端数据
            json_data = request.body
            # json.loads(a),将a转换成字典格式
            if not json_data:
                return to_json_data(errno=Code.PARAMERR, errmsg='参数为空，请重新输入！')
            dict_data = json.loads(json_data.decode('utf8'))
        except Exception as e:
            logging.info("错误信息，\n{}".format(e))
            return to_json_data(errno=Code.UNKOWNERR,errmsg=error_map[Code.UNKOWNERR])
            # 3、检验
        form=LoginForm(data=dict_data,request=request)
        # 5、 返回前端
        if form.is_valid():
            return to_json_data(errno=Code.OK,errmsg='恭喜您，登录成功！')
        else:
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)
class LogoutView(View):
    def get(self,request):
        logout(request)
        return redirect(reverse("users:login"))













