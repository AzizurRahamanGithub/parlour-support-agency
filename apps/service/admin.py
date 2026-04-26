from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from .models import Service, ServicePrice, Subscription, City, Country
from apps.auths.models import SocialMedia
from .forms import MultipleImagesForm
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
from .models import Category, ServiceLocation, Plan, SubCategory
from apps.auths.models import CustomUser

class ServicePriceInline(admin.TabularInline):
    model = ServicePrice
    extra = 1
    
class SocialMediaInline(admin.TabularInline):
    model = SocialMedia
    extra = 1    

class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1    

class CityInline(admin.TabularInline):
    model = City
    extra = 1    


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    form = MultipleImagesForm  # 🔥 connect your multi upload

    list_display = [ "user", "is_published", "get_plan"]
    filter_horizontal = ("category", "locations")
    # autocomplete_fields = ["category", "locations"]
    
    inlines = [ServicePriceInline]

    readonly_fields = ["subscription_info", "plan_limits"]

    fieldsets = (
        ("Basic Info", {
            "fields": ("user", "about", "is_published", "category", "locations")
        }),

        ("Images", {
            "fields": ( "upload_images",)  # 🔥 IMPORTANT
        }),

        ("Subscription", {
            "fields": ("subscription_info", "plan_limits")
        }),
    )

    # -------------------------
    # PLAN INFO
    # -------------------------
    def get_plan(self, obj):
        sub = Subscription.objects.filter(user=obj.user, is_active=True).first()
        return sub.plan.plan_name if sub else "No Plan"

    # -------------------------
    # SUBSCRIPTION INFO
    # -------------------------
    def subscription_info(self, obj):
        sub = Subscription.objects.filter(user=obj.user, is_active=True).first()
        if not sub:
            return "No Plan"

        return f"""
        Plan: {sub.plan.plan_name}
        Start: {sub.start_date}
        End: {sub.end_date}
        """

    # -------------------------
    # PLAN LIMIT
    # -------------------------
    def plan_limits(self, obj):
        sub = Subscription.objects.filter(user=obj.user, is_active=True).first()
        if not sub:
            return "No Plan"

        return f"""
        Max Images: {sub.plan.max_images}
        Max Videos: {sub.plan.max_videos}
        """

    # -------------------------
    # LIMIT VALIDATION
    # -------------------------
    def save_model(self, request, obj, form, change):
        from apps.file_uploader.upload_utils import upload_file_to_digital_ocean, delete_file_from_digital_ocean

        image_fields = {
            'upload_images_profile': ('image', 'user-profile'),
            'upload_images_licence': ('licence_image', 'user-licence'),
            'upload_images_id': ('id_image', 'user-id'),
            'upload_images_id_with': ('id_with_image', 'user-id-with-face'),
        }

        for field_key, (model_field, folder) in image_fields.items():
            # Delete selected
            to_delete = request.POST.getlist(f"delete_{model_field}")
            if to_delete:
                for url in to_delete:
                    try:
                        delete_file_from_digital_ocean(url)
                    except Exception:
                        pass
                current = getattr(obj, model_field, []) or []
                setattr(obj, model_field, [u for u in current if u not in to_delete])

            # Upload new files
            new_files = request.FILES.getlist(field_key)
            if new_files:
                all_urls = list(getattr(obj, model_field, []) or [])
                for f in new_files:
                    url = upload_file_to_digital_ocean(f, folder=folder)
                    all_urls.append(url)
                setattr(obj, model_field, list(dict.fromkeys(all_urls)))

            # ✅ new_files নেই, to_delete নেই — DB থেকে পুরনো value রাখো
            elif not to_delete:
                db_obj = CustomUser.objects.filter(pk=obj.pk).first()
                if db_obj:
                    current_val = getattr(db_obj, model_field, []) or []
                    setattr(obj, model_field, current_val)

        super().save_model(request, obj, form, change)
        
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    inlines = [SubCategoryInline]
    list_display = ["name", "created_at"]
    
@admin.register(Country)
class CountryAdmin(ModelAdmin):
    inlines = [CityInline]
    list_display = ["name", "created_at"]
         
@admin.register(Plan)
class PlanAdmin(ModelAdmin):

    list_display = [
        "plan_name",
        "stripe_price_id",
        "max_listings",
        "max_images",
        "max_videos",
        "is_vip_placement",
        "created_at",
    ]

    search_fields = ["plan_name", "stripe_price_id"]

    list_filter = [
        "plan_name",
        "is_vip_placement",
        "is_top_profile",
        "is_front_page",
    ]

    ordering = ["-created_at"]

    fieldsets = (
        ("Basic Info", {
            "fields": ("plan_name", "stripe_price_id")
        }),

        ("Limits", {
            "fields": (
                "max_listings",
                "max_categories",
                "max_locations",
                "max_images",
                "max_videos",
            )
        }),

        ("Features", {
            "fields": (
                "is_top_profile",
                "is_vip_placement",
                "is_front_page",
                "is_marketing",
                "monthly_bumps",
            )
        }),

        ("Support", {
            "fields": (
                "basic_support",
                "priority_support",
                "vip_support",
            )
        }),
    )
    
    
    
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status",
        "is_active",
        "stripe_subscription_id",
        "created_at",
    )

    list_filter = ("status", "is_active", "plan")
    search_fields = ("user__email", "stripe_subscription_id")    