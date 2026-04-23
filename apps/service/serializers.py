from django.db import models
from rest_framework import serializers
from .models import Service, Category, ServiceLocation, ServicePrice, Plan, SubCategory
from apps.auths.models import SocialMedia, CustomUser



class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"
        
        
class CategorySerializer(serializers.ModelSerializer):
    sub_category = SubCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = "__all__"


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"



class ServiceLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceLocation
        fields = "__all__"

class MiniServiceSerializer(serializers.ModelSerializer):
    category = CategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Service
        fields = ["id", "is_published", "category"]


class ServicePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePrice
        fields = ["id", "name", "price", "description"]
        
class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMedia
        fields = ["id", "platform", "username", "url"]     
        
class UserDetailesSerializer(serializers.ModelSerializer):
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
    plan_name = serializers.SerializerMethodField()
    location = ServiceLocationSerializer(many=True, read_only=True)
    service   = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "full_name",
            "photo",
            "plan_name",
            "location",
            "service"
        ]

    def get_plan_name(self, obj):
        if obj.current_plan and obj.current_plan.plan:
            return obj.current_plan.plan.plan_name
        return None
    
    def get_service(self, obj):
        services = obj.service_set.all() 
        return MiniServiceSerializer(services, many=True).data
          

class ServiceSerializer(serializers.ModelSerializer):
    # ── Nested write ──────────────────────────────────────
    category  = CategorySerializer(many=True, write_only=True, required=False)
    locations = ServiceLocationSerializer(many=True, write_only=True, required=False)
    prices    = ServicePriceSerializer(many=True, write_only=True, required=False)

    # ── Read only ─────────────────────────────────────────
    category_details  = CategorySerializer(source="category", many=True, read_only=True)
    location_details  = ServiceLocationSerializer(source="locations", many=True, read_only=True)
    price_details     = ServicePriceSerializer(source="prices", many=True, read_only=True)
    user_details      = UserDetailesSerializer(source="user", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "category", "locations", "prices",           # write
            "user_details", "category_details",           # read
            "location_details", "price_details",
            "about", "images", "is_published", "created_at",
        ]

    def create(self, validated_data):
        categories_data = validated_data.pop("category", [])
        locations_data  = validated_data.pop("locations", [])
        prices_data     = validated_data.pop("prices", [])

        service = Service.objects.create(**validated_data)

        # get_or_create — same name হলে duplicate হবে না
        for cat in categories_data:
            category, _ = Category.objects.get_or_create(name=cat["name"])
            service.category.add(category)

        for loc in locations_data:
            location = ServiceLocation.objects.create(user=service.user, **loc)
            service.locations.add(location)

        for price in prices_data:
            ServicePrice.objects.create(service=service, **price)

        return service
    
    def update(self, instance, validated_data):
        categories_data = validated_data.pop("category", None)
        locations_data  = validated_data.pop("locations", None)
        prices_data     = validated_data.pop("prices", None)

        # ── Simple fields update ──────────────────────────────
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # ── Categories ───────────────────────────────────────
        if categories_data is not None:
            instance.category.clear()  # পুরনো সব remove
            for cat in categories_data:
                category, _ = Category.objects.get_or_create(name=cat["name"])
                instance.category.add(category)

        # ── Locations ────────────────────────────────────────
        if locations_data is not None:
            instance.locations.clear()  # পুরনো সব remove
            for loc in locations_data:
                location = ServiceLocation.objects.create(user=instance.user, **loc)
                instance.locations.add(location)

        # ── Prices ───────────────────────────────────────────
        if prices_data is not None:
            instance.prices.all().delete()  # পুরনো সব delete
            for price in prices_data:
                ServicePrice.objects.create(service=instance, **price)

        return instance