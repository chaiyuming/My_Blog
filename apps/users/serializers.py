from rest_framework import serializers
from .models import User

class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=('id','telephone','username','is_active','is_staff','email','date_joined')
