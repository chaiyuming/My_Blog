import logging

from django.shortcuts import render
from django.views import View
from django.http import Http404


from . import models


logger=logging.getLogger('django')
# Create your views here.
class CourseListView(View):
    '''
    create  course list view
    '''
    def get(self,request):
        courses=models.Course.objects.select_related('teacher').only('title','cover_url','teacher__name','teacher__positional_title').filter(is_delete=False)
        return render(request,'course/course.html',locals())

class CourseDetailView(View):
    '''
    create course detail view
    route:"/course/<int:course_id>/
    '''
    def get(self,request,course_id):
        try:
            course=models.Course.objects.select_related('teacher').only('title', 'cover_url', 'video_url', 'profile', 'outline','teacher__name', 'teacher__avatar_url','teacher__positional_title', 'teacher__profile').filter(is_delete=False,id=course_id).first()
            return render(request,'course/course_detail.html',locals())
        except models.Course.DoesNotExist as e:
            logger.info("当前课程出现如下异常：\n{}".format(e))
            raise Http404("此课程不存在！")


