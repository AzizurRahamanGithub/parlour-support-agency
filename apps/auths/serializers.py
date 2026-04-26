from django.db.models import Avg, Count
from datetime import datetime, timedelta
from .models import CustomUser, ContactMessage, HelpUsImprove, UserProfile
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.service.serializers import PlanSerializer
from django.utils import timezone
import random

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    image = serializers.ListField(
        child=serializers.URLField(), required=False, default=list
    )
    licence_image = serializers.ListField(
        child=serializers.URLField(), required=False, default=list
    )
    id_image = serializers.ListField(
        child=serializers.URLField(), required=False, default=list
    )
    id_with_image = serializers.ListField(
        child=serializers.URLField(), required=False, default=list
    )

    class Meta:
        model = CustomUser
        fields = [
            "full_name", "email", "category",
            "image", "licence_image", "id_image", "id_with_image",
            "password",
        ]

    def validate(self, data):
        if CustomUser.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "Email already exists."})

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        password = validated_data.pop("password")

        image = validated_data.pop("image", [])
        licence_image = validated_data.pop("licence_image", [])
        id_image = validated_data.pop("id_image", [])
        id_with_image = validated_data.pop("id_with_image", [])

        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        base_username = (first_name + last_name).lower()
        username = base_username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        otp = str(random.randint(100000, 999999))

        user = CustomUser.objects.create(
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=validated_data["email"],
            category=validated_data.get("category", ""),
            image=image,
            licence_image=licence_image,
            id_image=id_image,
            id_with_image=id_with_image,
            is_active=False,
            email_verified=False
        )

        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.otp = otp
        profile.otp_created_at = timezone.now()
        profile.save()

        self.otp = otp
        self.user_instance = user

        return user
    
 
class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs.get("email")
        otp = attrs.get("otp")

        try:
            profile = UserProfile.objects.select_related("user").get(user__email=email)
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("User not found")

        if not profile.otp:
            raise serializers.ValidationError("No OTP found")

        if profile.is_otp_expired():
            raise serializers.ValidationError("OTP expired")

        if profile.otp != otp:
            raise serializers.ValidationError("Invalid OTP")

        attrs["profile"] = profile
        return attrs
 
    
class CustomUserAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'is_active', 'full_name',
                  'email', 'category', 'address', 'phone_number', 'photo',]
        

class UserSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'full_name', 'email', 'designation', 'is_active', 'plan',
                  'category', 'address', 'phone_number', 'photo', 'created_at')
        read_only_fields = ('id', 'username', 'email', 'is_active',)

    def create(self, validated_data):
        return User.objects.create(**validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)        
    

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data['identifier']
        password = data['password']

        # 🔍 find user
        if '@' in identifier and '.' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(username=identifier).first()

        if not user:
            raise serializers.ValidationError({
                "identifier": "Invalid credentials."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "identifier": "Account inactive."
            })

        if not user.check_password(password):
            raise serializers.ValidationError({
                "password": "Incorrect password."
            })

        user = authenticate(username=user.username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        # 🔥 ONLY return user
        return {"user": user}


class TokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "User with this email does not exist.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                "New password and confirmation password do not match.")
        return data


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "full_name", "email", "subject", "message", "created_at"]
        read_only_fields = ["id", "created_at"]
 
        
class HelpUsImproveSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = HelpUsImprove
        fields = ["id", "user", "improve_message"]
        read_only_fields = ["user"]        
        


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "email", "username", "password", "full_name",
            "category", "is_active", "address", "phone_number", "photo"
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user        