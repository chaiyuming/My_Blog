import logging


from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.http import FileResponse,Http404
from django.utils.encoding import escape_uri_path
import requests

from . import models


logger = logging.getLogger('django')
# Create your views here.
def Docfile(request):
    '''
    download view
    '''
    docs=models.Doc.objects.only('title','desc','image_url','file_url').filter(is_delete=False)
    return render(request,'doc/docDownload.html',locals())

class DocDownload(View):
    '''
    create doc download view
    url:'/doc_download/<int:doc_id>'
    '''
    def get(self,request,doc_id):
        doc=models.Doc.objects.only('file_url').filter(is_delete=False,id=doc_id).first()
        if doc:
            doc_url=doc.file_url
            doc_url=settings.SITE_DOMAIN_PORT+doc_url if not doc_url.startswith('http') else doc_url
            try:
                # requests.get()时爬虫的方法，获取指定的url的内容，FileResponse()实现下载功能，在FileResponse中使用了缓存，更加节省资源
                res=FileResponse(requests.get(doc_url,stream=True))
            except Exception as e:
                logger.info('获取文档内容出现异常：{}'.format(e))
                raise Http404('文档下载异常')
            # 获取文件后缀名
            ex_name=doc_url.split('.')[-1]
            if not ex_name:
                raise Http404('文档url异常！')
            else:
                ex_name=ex_name.lower()
            # 对文档后缀名进行判断
            if ex_name =="pdf":
                res["Content-type"] = "application/pdf"
            elif ex_name == "zip":
                res["Content-type"] = "application/zip"
            elif ex_name == "doc":
                res["Content-type"] = "application/msword"
            elif ex_name == "xls":
                res["Content-type"] = "application/vnd.ms-excel"
            elif ex_name == "docx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ex_name == "ppt":
                res["Content-type"] = "application/vnd.ms-powerpoint"
            elif ex_name == "pptx":
                res["Content-type"] = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            else:
                raise Http404("文档格式不正确！")
            final_docname=doc.title + "." + ex_name
            doc_name=escape_uri_path(final_docname)
            # attachment处设置为inline，会直接打开。
            res["Content-Disposition"] = "attachment; filename*=UTF-8''{}".format(doc_name)
            return res
        else:
            raise Http404('文档不存在！')








