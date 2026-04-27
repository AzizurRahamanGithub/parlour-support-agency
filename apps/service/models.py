from django.db import models
from django.conf import settings
# Create your models here.
import stripe

class Category(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    description= models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name 

class SubCategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.category.name} → {self.name}"   


class Country(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name


class City(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="cities"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ("country", "name")

    def __str__(self):
        return f"{self.country.name} → {self.name}"
    
       
class ServiceLocation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location",
        null=True, blank=True
    )
    country = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.city}, {self.country}"
    
class Plan(models.Model):
    PLAN_TYPE = [
        ("basic", "Basic"),
        ("premium", "Premium"),
        ("business", "Business"),
    ]
    
    plan_name = models.CharField(max_length=15, choices=PLAN_TYPE, unique=True)

    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    # Limits
    max_listings = models.IntegerField(default=1)
    max_categories = models.IntegerField(default=1)
    max_sub_categories = models.IntegerField(default=1)
    max_locations = models.IntegerField(default=1)
    max_images = models.IntegerField(default=8)
    max_videos = models.IntegerField(default=1)

    # Features
    is_top_profile = models.BooleanField(default=False)
    is_vip_placement = models.BooleanField(default=False)
    is_front_page = models.BooleanField(default=False)
    is_marketing = models.BooleanField(default=False)

    monthly_bumps = models.IntegerField(default=2)

    # Support
    priority_support = models.BooleanField(default=False)
    basic_support = models.BooleanField(default=False)
    vip_support = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.plan_name  
        

class Service(models.Model):
    is_published = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    about= models.TextField(null=True, blank=True)
    category = models.ManyToManyField(Category, blank=True)
    subcategory = models.ManyToManyField(SubCategory, blank=True) 
    country = models.ManyToManyField(Country, blank=True) 
    city = models.ManyToManyField(City, blank=True)
    locations = models.ManyToManyField(ServiceLocation, blank=True)
    images = models.JSONField(default=list, blank=True)
    social_media = models.ManyToManyField('auths.SocialMedia', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
class ServicePrice(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="prices")

    name = models.CharField(max_length=200, blank=True, null=True) 
    price = models.PositiveIntegerField( blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name    
    
    
class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("past_due", "Past Due"),
        ("incomplete", "Incomplete"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)

    stripe_customer_id = models.CharField(max_length=100)
    stripe_subscription_id = models.CharField(max_length=100)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.user} - {self.plan}"
    
    
class AddOn(models.Model):
    ADDON_TYPE_CHOICES = [
        ("front_page_listing", "Front Page Listing"),
        ("top_profile_placement", "Top Profile Placement"),
        ("additional_location", "Additional Location"),
        ("additional_categories", "Additional Categories"),
        ("additional_bumps", "2 Additional Bumps"),
    ]

    name = models.CharField(max_length=100)
    addon_type = models.CharField(max_length=50, choices=ADDON_TYPE_CHOICES, unique=True)
    stripe_price_id = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # auto fill হবে
    extra_limit = models.IntegerField(default=1)  # additional location/category কতটা extra পাবে

    def save(self, *args, **kwargs):
        # stripe_price_id থেকে price auto fetch
        if self.stripe_price_id and not self.price:
            try:
                stripe_price = stripe.Price.retrieve(self.stripe_price_id)
                self.price = stripe_price["unit_amount"] / 100  # cents to dollars
            except Exception as e:
                print("Stripe price fetch error:", e)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name    
    
    
class UserAddOn(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addons")
    addon = models.ForeignKey(AddOn, on_delete=models.CASCADE)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.addon.name}"    