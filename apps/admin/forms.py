from django import forms

from apps.news.models import News,Banner,Tag
from apps.doc.models import Doc
from apps.course.models import Course,Teacher,CourseCategory


class NewsPubForm(forms.ModelForm):
    """
    """
    image_url = forms.URLField(label='文章图片url',
                               error_messages={"required": "文章图片url不能为空"})
    tag = forms.ModelChoiceField(queryset=Tag.objects.only('id').filter(is_delete=False),
                                 error_messages={"required": "文章标签id不能为空", "invalid_choice": "文章标签id不存在", }
                                 )
    class Meta:
        model = News  # 与数据库模型关联
        # 需要关联的字段
        # exclude 排除
        fields = ['title', 'digest', 'content', 'image_url', 'tag']
        error_messages = {
            'title': {
                'max_length': "文章标题长度不能超过150",
                'min_length': "文章标题长度大于1",
                'required': '文章标题不能为空',
            },
            'digest': {
                'max_length': "文章摘要长度不能超过200",
                'min_length': "文章标题长度大于1",
                'required': '文章摘要不能为空',
            },
            'content': {
                'required': '文章内容不能为空',
            },
        }

class DocForms(forms.ModelForm):
    image_url=forms.URLField(label='文档缩略图url',error_messages={
        "required": "文档缩略图url不能为空"
    })
    file_url = forms.URLField(label='文档url',
                               error_messages={"required": "文档url不能为空"})
    class Meta:
        model=Doc
        fields=['title','image_url','file_url','desc']
        error_messages={
            'title':{
                'max_length': "文档标题长度不能超过150",
                'min_length': "文档标题长度大于1",
                'required': '文档标题不能为空',
            },
            'desc':{
                'max_length': "文档摘要长度不能超过200",
                'min_length': "文档标题长度大于1",
                'required': '文档摘要不能为空',
            }
        }
class CourseForms(forms.ModelForm):
    teacher=forms.ModelChoiceField(Teacher.objects.only('id').filter(is_delete=False),
                                   error_messages={
                                       'required':'教师id不能为空',
                                       "invalid_choice":'教师id不能为空'
                                   })
    category=forms.ModelChoiceField(CourseCategory.objects.only('id').filter(is_delete=False),
                                    error_messages={
                                        'required': '课程标签id不能为空',
                                        "invalid_choice": '课程标签id不能为空'
                                    })
    video_url=forms.URLField(label='视频URL',error_messages={
        "required":'课程视频URL不能为空'
    })
    cover_url=forms.URLField(label='课程封面图URL',error_messages={
        "required":'课程封面图URL不能为空'
    })
    class Meta:
        model=Course
        fields=['title','cover_url','video_url','duration','profile','outline','teacher','category']
        error_messages = {
            'title': {
                'max_length': "视频标题长度不能超过150",
                'min_length': "视频标题长度大于1",
                'required': '视频标题不能为空',
            },
            'duration': {
                'required': '课程时长不能为空',
            },
        }