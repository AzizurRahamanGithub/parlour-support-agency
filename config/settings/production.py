
import os
from .base import *

# CRITICAL: Production MUST have DEBUG = False
DEBUG = False

# Database: Use PostgreSQL for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'db'),  # 'db' for Docker
        'PORT': os.environ.get('DB_PORT', '5432'),
        # Performance optimizations
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Static files for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


ALLOWED_HOSTS = ['2.24.66.200', 'localhost', '127.0.0.1']

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://2.24.66.200:3000',  # frontend
    'http://2.24.66.200:8000',  # backend
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://2.24.66.200:3000',
    'http://2.24.66.200:8000',
]



# Update DRF settings for production
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour',  # Adjust based on your needs
        'anon': '100/hour',   # Adjust based on your needs
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
})



# Logging configuration for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
}


# Security headers
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

print("✅ Production settings loaded")
