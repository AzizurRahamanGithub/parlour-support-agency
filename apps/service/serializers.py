from django.db import models
from rest_framework import serializers
from .models import Service, Category, ServiceLocation, ServicePrice, Plan, SubCategory, City, Country
from apps.auths.models import SocialMedia, CustomUser
import stripe
from django.conf import settings
stripe.api_key = settings.STRIPE_SECRET_KEY


class SelectedSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):  # ✅ আগে define করো
    subcategories = SelectedSubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'subcategories']


class CategoryWithSelectedSubSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'subcategories']

    def get_subcategories(self, obj):
        selected_ids = self.context.get('selected_subcategory_ids', [])
        subs = obj.subcategories.filter(id__in=selected_ids)
        return SelectedSubCategorySerializer(subs, many=True).data


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name"]


class CountrySerializer(serializers.ModelSerializer):
    cities = CitySerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = ["id", "name", "cities"]


class PlanSerializer(serializers.ModelSerializer):
    stripe_price = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = "__all__"

    def get_stripe_price(self, obj):
        if not obj.stripe_price_id:
            return None
        try:
            price = stripe.Price.retrieve(obj.stripe_price_id)
            return price.unit_amount // 100
        except Exception:
            return None


class ServiceLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceLocation
        fields = "__all__"


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
    image = serializers.ListField(
        child=serializers.URLField(), read_only=True, default=list  # ✅ fix
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_name",
            "image",
            "phone_number",
            "designation",
            "social_media",
        ]


class MiniServiceSerializer(serializers.ModelSerializer):
    # শুধু selected subcategory দেখাবে
    category = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ["id", "is_published", "category"]

    def get_category(self, obj):
        selected_sub_ids = list(obj.subcategory.values_list('id', flat=True))
        return CategoryWithSelectedSubSerializer(
            obj.category.all(),
            many=True,
            context={'selected_subcategory_ids': selected_sub_ids}
        ).data


class UserSerializer(serializers.ModelSerializer):
    plan_name        = serializers.SerializerMethodField()
    profile_image    = serializers.SerializerMethodField()
    country          = serializers.SerializerMethodField()
    category_details = serializers.SerializerMethodField()
    service          = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "full_name",
            "profile_image",
            "plan_name",
            "country",
            "category_details",
            "service",
        ]

    def get_profile_image(self, obj):
        # JSON list থেকে প্রথম image
        if obj.image and isinstance(obj.image, list) and len(obj.image) > 0:
            return obj.image[0]
        return None

    def get_plan_name(self, obj):
        if obj.current_plan and obj.current_plan.plan:
            return obj.current_plan.plan.plan_name
        return None

    def get_country(self, obj):
        # user-এর service-এর city থেকে country
        countries = []
        for service in obj.service_set.all():
            for country in service.country.all():
                if country.name not in countries:
                    countries.append(country.name)
        return countries

    def get_category_details(self, obj):
        categories = []
        for service in obj.service_set.all():
            for cat in service.category.all():
                if not any(c["id"] == cat.id for c in categories):
                    categories.append({
                        "id": cat.id,
                        "name": cat.name,
                    })
        return categories

    def get_service(self, obj):
        services = obj.service_set.filter(is_published=True)
        return MiniServiceSerializer(services, many=True).data

class ServiceSerializer(serializers.ModelSerializer):
    # ── Write ─────────────────────────────────────────────
    subcategory  = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), many=True, write_only=True, required=False
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), many=True, write_only=True, required=False
    )
    service_details = ServicePriceSerializer(many=True, write_only=True, required=False)
    social_media = SocialMediaSerializer(many=True, write_only=True, required=False) 
    phone_number = serializers.CharField(write_only=True, required=False)

    # ── Read only ─────────────────────────────────────────
    category_details     = serializers.SerializerMethodField(read_only=True)
    location_details     = serializers.SerializerMethodField(read_only=True)
    price_details        = ServicePriceSerializer(source="prices", many=True, read_only=True)
    user_details         = UserDetailesSerializer(source="user", read_only=True)
    social_media_details = SocialMediaSerializer(source="social_media", many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "subcategory", "city", "service_details", "phone_number", "social_media",
            "user_details", "category_details",
            "location_details", "price_details", "social_media_details",
            "about", "images", "videos", "is_published", "created_at",
        ]
        
    def get_category_details(self, obj):
        return [
            {"id": sub.category.id, "name": sub.category.name}
            for sub in obj.subcategory.select_related("category").all()
        ]

    def get_location_details(self, obj):
        return [
            {"id": city.id, "name": city.name}
            for city in obj.city.all()
        ]    

    def create(self, validated_data):
        subcategories  = validated_data.pop("subcategory", [])
        cities         = validated_data.pop("city", [])
        prices_data    = validated_data.pop("service_details", [])
        social_medias  = validated_data.pop("social_media", [])  # ✅

        service = Service.objects.create(**validated_data)

        service.subcategory.set(subcategories)
        self._set_categories_from_subcategories(service, subcategories)
        service.city.set(cities)
        self._set_countries_from_cities(service, cities)
        
        phone_number = validated_data.pop("phone_number", None)
        if phone_number:
            service.user.phone_number = phone_number
            service.user.save(update_fields=["phone_number"])

        # ✅ Create social media and link to service
        for sm_data in social_medias:
            social = SocialMedia.objects.create(user=service.user, **sm_data)
            service.social_media.add(social)

        for price in prices_data:
            ServicePrice.objects.create(service=service, **price)

        return service

    def update(self, instance, validated_data):
        subcategories  = validated_data.pop("subcategory", None)
        cities         = validated_data.pop("city", None)
        prices_data    = validated_data.pop("service_details", None)
        social_medias  = validated_data.pop("social_media", None)  # ✅

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if subcategories is not None:
            instance.subcategory.set(subcategories)
            self._set_categories_from_subcategories(instance, subcategories)
            
        phone_number = validated_data.pop("phone_number", None)
        if phone_number:
            instance.user.phone_number = phone_number
            instance.user.save(update_fields=["phone_number"])    

        if cities is not None:
            instance.city.set(cities)
            self._set_countries_from_cities(instance, cities)

        # ✅ Delete old and create new social media
        if social_medias is not None:
            instance.social_media.all().delete()
            for sm_data in social_medias:
                social = SocialMedia.objects.create(user=instance.user, **sm_data)
                instance.social_media.add(social)

        if prices_data is not None:
            instance.prices.all().delete()
            for price in prices_data:
                ServicePrice.objects.create(service=instance, **price)

        return instance