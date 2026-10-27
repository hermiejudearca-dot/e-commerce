
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

    # Honeybail application
    "product",
    "storefront",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",

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
            default="123456789",
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

# Keep Django's default User model.
# The Customer model is linked to it through a OneToOneField.

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

# Note:
# REST_FRAMEWORK permissions apply to DRF views.
# The existing Honeybail JsonResponse views use their own
# authentication and permission checks.


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


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# CORS CONFIGURATION
# ============================================================

# Allows the local HTML/JavaScript frontend to communicate
# with Django when using VS Code Live Server.

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://192.168.0.248:5500",
]

# Allows browser session cookies to be sent with API requests.

CORS_ALLOW_CREDENTIALS = True


# ============================================================
# CSRF PROTECTION
# ============================================================

# Trusted local frontend origins for unsafe requests,
# including POST, PATCH, PUT, and DELETE.

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

# Keep CSRF protection enabled.
# The frontend must send the CSRF token with write requests.

CSRF_COOKIE_HTTPONLY = False

CSRF_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SAMESITE = "Lax"


# ============================================================
# SESSION CONFIGURATION
# ============================================================

# Django sessions will maintain customer login state.

SESSION_ENGINE = "django.contrib.sessions.backends.db"

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

# During development, emails appear in the terminal.
# Configure a real email service before deployment.

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
