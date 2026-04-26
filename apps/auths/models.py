from datetime import datetime, time, timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import timedelta
import string
import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from import_export.admin import ImportExportActionModelAdmin
from apps.service.models import Subscription
now = timezone.now()
from django.contrib import admin
import random
from apps.service.models import Category

class FixedCategory(models.TextChoices):
    ADMIN = 'bliss', 'BLISS'
    LEARNER = 'beauty', 'BEAUTY'


class SocialMedia(models.Model):
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_media"
    )

    SOCIAL_TYPE_CHOICES = [
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("twitter", "Twitter / X"),
        ("linkedin", "LinkedIn"),
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
        ("github", "GitHub"),
        ("website", "Website"),
    ]

    platform = models.CharField(max_length=50, choices=SOCIAL_TYPE_CHOICES)
    username = models.CharField(max_length=150, blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.platform} - {self.username or self.url}"

    

class CustomUser(AbstractUser):
    current_plan = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL)
    email_verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    is_active= models.BooleanField(default=True)
    category = models.CharField(max_length=10, choices=FixedCategory.choices, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    designation = models.CharField(
        max_length=15, null=True, blank=True)
    phone_number = models.CharField(
        max_length=15, null=True, blank=True)
    image = models.JSONField(default=list, blank=True)
    licence_image = models.JSONField(default=list, blank=True)
    id_image = models.JSONField(default=list, blank=True)
    id_with_image = models.JSONField(default=list, blank=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email'], name='email_idx'),
            models.Index(fields=['username'], name='username_idx'),
            models.Index(fields=['created_at'], name='created_at_idx'),
        ]


class CustomUserAdmin(ImportExportActionModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'full_name')


class UserProfile(models.Model):
    user = models.OneToOneField("CustomUser", on_delete=models.CASCADE)
    
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    reset_token = models.CharField(max_length=100, null=True, blank=True)
    reset_token_expires = models.DateTimeField(null=True, blank=True)

    # 🔥 OTP generate
    def generate_otp(self):
        return str(random.randint(100000, 999999))

    # 🔥 set OTP
    def set_otp(self):
        self.otp = self.generate_otp()
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp

    # 🔥 OTP expiry check
    def is_otp_expired(self):
        if self.otp_created_at:
            return timezone.now() > self.otp_created_at + timedelta(minutes=10)
        return True

    # 🔥 reset token generate
    def generate_reset_token(self):
        self.reset_token = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=32)
        )
        self.reset_token_expires = timezone.now() + timedelta(minutes=5)
        self.save()
        return self.reset_token

    def is_reset_token_expired(self):
        if self.reset_token_expires:
            return timezone.now() > self.reset_token_expires
        return True

    def __str__(self):
        return f"Profile of {self.user.email}"


class ContactMessage (models.Model):
    full_name= models.CharField(max_length=200)
    email= models.EmailField()
    subject= models.CharField(max_length=300)
    message= models.TextField()
    created_at= models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    def __str__(self):
        return f"{self.full_name}-{self.subject}"
    
class HelpUsImprove(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="improving") 
    improve_message= models.TextField()
    
    def __str__(self):
        return f"{self.user.full_name}-{self.improve_message}"