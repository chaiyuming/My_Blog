from django.shortcuts import render
from django.views import View

# Create your views here.

def Login(request):
    '''
    用户登录页面
    :param request:
    :return:
    '''
    return render(request,'users/login.html')

def Register(request):
    '''
    用户注册页面
    :param request:
    :return:
    '''
    return render(request,'users/register.html')