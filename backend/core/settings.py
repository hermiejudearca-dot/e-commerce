
"""
Django settings for Honeybail e-commerce project.

Backend: Django
Database: PostgreSQL
Frontend: HTML, CSS, JavaScript
"""

from pathlib import Path
from decouple import config


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY SETTINGS
# ============================================================

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-key-change-before-deployment",
)

DEBUG = config(
    "DJANGO_DEBUG",
    default=True,
    cast=bool,
)

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "192.168.0.248",
    "e-commerce-w987.onrender.com",
]


# ============================================================
# INSTALLED APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Django built-in applications
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party applications
    "rest_framework",
    "corsheaders",

    # Honeybail applications
    "product",
    "storefront",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Serve collected static files on Render
    "whitenoise.middleware.WhiteNoiseMiddleware",

    # CORS support
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "core.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# WSGI APPLICATION
# ============================================================

WSGI_APPLICATION = "core.wsgi.application"


# ============================================================
# POSTGRESQL DATABASE CONFIGURATION
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",

        "NAME": config(
            "DB_NAME",
            default="e_commerce_db",
        ),

        "USER": config(
            "DB_USER",
            default="postgres",
        ),

        "PASSWORD": config(
            "DB_PASSWORD",
            default="12345678",
        ),

        "HOST": config(
            "DB_HOST",
            default="localhost",
        ),

        "PORT": config(
            "DB_PORT",
            default="5432",
        ),
    }
}


# ============================================================
# AUTHENTICATION AND PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}


# ============================================================
# LANGUAGE AND TIMEZONE
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Manila"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise serves collected CSS and JavaScript files,
# including Django Admin's static assets.

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
        ),
    },
}


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# CORS CONFIGURATION
# ============================================================

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

CORS_ALLOW_CREDENTIALS = True


# ============================================================
# CSRF PROTECTION
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

CSRF_COOKIE_HTTPONLY = False

CSRF_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SAMESITE = "Lax"


# ============================================================
# SESSION CONFIGURATION
# ============================================================

SESSION_ENGINE = (
    "django.contrib.sessions.backends.db"
)

SESSION_COOKIE_AGE = 60 * 60 * 24 * 7

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_SAMESITE = "Lax"

SESSION_SAVE_EVERY_REQUEST = False


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)
