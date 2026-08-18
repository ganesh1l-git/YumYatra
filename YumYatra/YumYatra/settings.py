"""
Django settings for YumYatra project.

Optimized for local development and serverless deployment (Vercel).
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR.parent / '.env')

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-g0z#fr-hr2)ls@6wage!iyc#6ge_5e+e$(z%e)xuk$0lq6y2*^'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't', 'yes')

# Allowed Hosts
allowed_hosts_raw = os.getenv('ALLOWED_HOSTS', '*')
if allowed_hosts_raw == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_raw.split(',') if h.strip()]

# CSRF Trusted Origins for Vercel and localhost
csrf_origins_raw = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://*.vercel.app,https://*.now.sh,http://127.0.0.1,http://localhost'
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_raw.split(',') if o.strip()]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'delivery',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'YumYatra.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'YumYatra.wsgi.application'


# Database Configuration
database_url = os.getenv('DATABASE_URL', '').strip()

if database_url:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Check if running on Vercel Serverless environment
    is_vercel = os.getenv('VERCEL') == '1' or os.getenv('VERCEL_ENV') is not None
    if is_vercel:
        tmp_db = Path('/tmp/db.sqlite3')
        orig_db = BASE_DIR / 'db.sqlite3'
        if not tmp_db.exists() and orig_db.exists():
            try:
                shutil.copyfile(orig_db, tmp_db)
            except Exception:
                pass
        db_path = tmp_db if tmp_db.exists() else orig_db
    else:
        db_path = BASE_DIR / 'db.sqlite3'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path,
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage configuration
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Payment Gateway Configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_Sm51ApkHEN14cp')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'Kp9U7TYW1N69IGWfyFMOut1w')
