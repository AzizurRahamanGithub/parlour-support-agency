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
        child=serializers.URLField(), read_only=True, default=list
    )
    current_plan = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_name",
            "image",
            "phone_number",
            "current_plan",
            "social_media",
        ]

    def get_current_plan(self, obj):
        if obj.current_plan and obj.current_plan.plan:
            return {
                "status": obj.current_plan.status,
                "is_active": obj.current_plan.is_active,
                "start_date": obj.current_plan.start_date,
                "end_date": obj.current_plan.end_date,
                "plan": PlanSerializer(obj.current_plan.plan).data,
            }
        return None

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

    # def get_service(self, obj):
    #     services = obj.service_set.filter(is_published=True)
    #     return MiniServiceSerializer(services, many=True).data
    def get_service(self, obj):
        service = obj.service_set.first()
        return MiniServiceSerializer(service).data





class ServiceSerializer(serializers.ModelSerializer):
    # ── Write ─────────────────────────────────────────────
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), many=True, write_only=True, required=False
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), many=True, write_only=True, required=False
    )
    full_name = serializers.CharField(write_only=True, required=False)
    service_details = ServicePriceSerializer(many=True, write_only=True, required=False)
    social_media = SocialMediaSerializer(many=True, write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)
    image = serializers.CharField(write_only=True, required=False)
    # ── Read only ─────────────────────────────────────────
    category_details = serializers.SerializerMethodField(read_only=True)
    location_details = serializers.SerializerMethodField(read_only=True)
    price_details    = ServicePriceSerializer(source="prices", many=True, read_only=True)
    user_details     = UserDetailesSerializer(source="user", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "image", "full_name",
            "subcategory", "city", "service_details", "phone_number", "social_media",
            "user_details", "category_details",
            "location_details", "price_details",
            "about", "images", "videos", "is_published", "created_at",
        ]

    def validate(self, attrs):
        price_details = self.initial_data.get("price_details")
        if price_details is not None:
            attrs["service_details"] = price_details
        return attrs

    def _set_categories_from_subcategories(self, service, subcategories):
        categories = set()
        for sub in subcategories:
            if sub.category:
                categories.add(sub.category)
        service.category.set(list(categories))

    def _set_countries_from_cities(self, service, cities):
        countries = set()
        for city in cities:
            if city.country:
                countries.add(city.country)
        service.country.set(list(countries))

    def get_category_details(self, obj):
        category_map = {}
        for sub in obj.subcategory.select_related("category").all():
            cat_id = sub.category.id
            if cat_id not in category_map:
                category_map[cat_id] = {
                    "id": cat_id,
                    "name": sub.category.name,
                    "subcategories": []
                }
            category_map[cat_id]["subcategories"].append({
                "id": sub.id,
                "name": sub.name
            })
        return list(category_map.values())[0] if category_map else {}

    def get_location_details(self, obj):
        country_map = {}
        for city in obj.city.select_related("country").all():
            country_id = city.country.id
            if country_id not in country_map:
                country_map[country_id] = {
                    "id": country_id,
                    "name": city.country.name,
                    "cities": []
                }
            country_map[country_id]["cities"].append({
                "id": city.id,
                "name": city.name
            })
        return list(country_map.values())[0] if country_map else {}

    def create(self, validated_data):
        subcategories = validated_data.pop("subcategory", [])
        cities        = validated_data.pop("city", [])
        prices_data   = validated_data.pop("service_details", [])
        social_medias = validated_data.pop("social_media", [])
        phone_number  = validated_data.pop("phone_number", None)

        service = Service.objects.create(**validated_data)

        service.subcategory.set(subcategories)
        self._set_categories_from_subcategories(service, subcategories)
        service.city.set(cities)
        self._set_countries_from_cities(service, cities)

        if phone_number:
            service.user.phone_number = phone_number
            service.user.save(update_fields=["phone_number"])

        for sm_data in social_medias:
            social = SocialMedia.objects.create(user=service.user, **sm_data)
            service.social_media.add(social)

        for price in prices_data:
            ServicePrice.objects.create(service=service, **price)

        return service

    def update(self, instance, validated_data):
        subcategories = validated_data.pop("subcategory", None)
        cities        = validated_data.pop("city", None)
        prices_data   = validated_data.pop("service_details", None)
        social_medias = validated_data.pop("social_media", None)
        phone_number  = validated_data.pop("phone_number", None)
        image         = validated_data.pop("image", None)
        full_name     = validated_data.pop("full_name", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if subcategories is not None:
            instance.subcategory.set(subcategories)
            self._set_categories_from_subcategories(instance, subcategories)

        if cities is not None:
            instance.city.set(cities)
            self._set_countries_from_cities(instance, cities)

        user_updated = False
        if phone_number:
            instance.user.phone_number = phone_number
            user_updated = True
        if image:
            instance.user.image = [image]
            user_updated = True
        if full_name:
            instance.user.full_name = full_name
            user_updated = True
        if user_updated:
            instance.user.save()

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
    
    
    