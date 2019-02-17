from django.shortcuts import render
from django.views import View

# Create your views here.

def index(request):
    '''
    首页
    :param request:
    :return:
    '''
    return render(request,'news/index.html')
