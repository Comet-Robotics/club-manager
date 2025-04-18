"""
Django settings for clubManager project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from platformdirs import PlatformDirs

dirs = PlatformDirs(appauthor="Comet Robotics", appname="Club Manager", ensure_exists=True)

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


PUBLIC_URL = os.getenv("PUBLIC_URL")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv("SECRET_KEY"))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(os.getenv("DEBUG", "0")))

CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
ALLOWED_HOSTS = []
CSRF_TRUSTED_ORIGINS = []

if PUBLIC_URL:
    ALLOWED_HOSTS += [PUBLIC_URL]
    CSRF_TRUSTED_ORIGINS += [PUBLIC_URL]
else:
    print("Warning: PUBLIC_URL not set. Things might break.")

if DEBUG:
    ALLOWED_HOSTS += ["127.0.0.1", "*"]
    CSRF_TRUSTED_ORIGINS += ["http://127.0.0.1", "http://localhost:5173"]


# Application definition

INSTALLED_APPS = [
    "core.apps.CoreConfig",
    "posters.apps.PostersConfig",
    "events.apps.EventsConfig",
    "payments.apps.PaymentsConfig",
    "accounts.apps.AccountsConfig",
    "projects.apps.ProjectsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_tables2",
    "django_rename_app",
    "django_extensions",
    "computedfields",
    "more_admin_filters",
    "rest_framework",
    "drf_spectacular",
    "django_vite",
    "multiselectfield",
    "colorfield",
]


DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "static_url_prefix": "" if DEBUG else "/vite/",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Comet Robotics Club Manager API",
    "DESCRIPTION": "Link shortener, attendance tracking, Discord bot, and other utilities for managing club operations",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": True,
    # OTHER SETTINGS
}

DISABLE_CSRF = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    ("django.middleware.csrf.CsrfViewMiddleware" if not DISABLE_CSRF else "common.middle.DisableCSRFMiddleware"),
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "clubManager.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
            ],
        },
    },
]

WSGI_APPLICATION = "clubManager.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": str(os.getenv("DB_NAME")),
        "USER": str(os.getenv("DB_USER")),
        "PASSWORD": str(os.getenv("DB_PASSWORD")),
        "HOST": str(os.getenv("DB_HOST")),
        "PORT": str(os.getenv("DB_PORT")),  # default PostgreSQL port
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.getenv("STATIC_ROOT")
MEDIA_ROOT = dirs.user_data_path / "media"
MEDIA_URL = "/media/"

STATICFILES_DIRS = [
    BASE_DIR / "frontend/dist",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/profile/"
SQUARE_APPLE_MERCHANT_ID = os.getenv("SQUARE_APPLE_MERCHANT_ID")

# Email Settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = str(os.getenv("SMTP_SERVER"))
EMAIL_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = str(os.getenv("SMTP_USER"))
EMAIL_HOST_PASSWORD = str(os.getenv("SMTP_PASS"))

# Discord Integration settings
DISCORD_TOKEN = str(os.getenv("DISCORD_TOKEN"))
DISCORD_SERVER_ID = int(str(os.getenv("DISCORD_SERVER_ID")))
DISCORD_OFFICER_ROLE_ID = int(str(os.getenv("DISCORD_OFFICER_ROLE_ID")))
DISCORD_PROJECT_MANAGER_ROLE_ID = int(str(os.getenv("DISCORD_PROJECT_MANAGER_ROLE_ID")))
DISCORD_TEAM_LEAD_ROLE_ID = int(str(os.getenv("DISCORD_TEAM_LEAD_ROLE_ID")))
DISCORD_MEMBER_ROLE_ID = int(str(os.getenv("DISCORD_MEMBER_ROLE_ID")))

ENABLE_SQUARE_PAYMENTS = bool(int(os.getenv("ENABLE_SQUARE_PAYMENTS", 0)))
