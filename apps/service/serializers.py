from django.db import models
from rest_framework import serializers
from .models import Service, Category, ServiceLocation, ServicePrice
from apps.auths.models import SocialMedia, Designation, CustomUser


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ServiceLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceLocation
        fields = "__all__"


class ServicePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePrice
        fields = "__all__"

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ["id", "name"]
        
class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMedia
        fields = ["id", "platform", "username", "url"]     
        
class UserDetailesSerializer(serializers.ModelSerializer):
    designation = DesignationSerializer(many=True, read_only=True)
    social_media = SocialMediaSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_name",
            "photo",
            "phone_number",
            "designation",
            "social_media",
        ]

    def get_current_plan(self, obj):
        return obj.current_plan.plan_name if obj.current_plan else None       
    
class UserSerializer(serializers.ModelSerializer):
    current_plan = serializers.SerializerMethodField()
    location= serializers.ServiceLocationSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "full_name",
            "photo",
            "current_plan",
            "location"
        ]

    def get_current_plan(self, obj):
        return obj.current_plan.plan_name if obj.current_plan else None          

class ServiceSerializer(serializers.ModelSerializer):
    category = CategorySerializer(many=True, read_only=True)
    locations = ServiceLocationSerializer(many=True, read_only=True)
    prices = ServicePriceSerializer(many=True, read_only=True)

    user = serializers.UserDetailesSerializer()

    class Meta:
        model = Service
        fields = [
            "id",
            "user",
            "about",
            "gallery",
            "category",
            "locations",
            "prices",
            "created_at",
        ]
