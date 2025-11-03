"""
Django settings for population_site project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url  # add this

# Load .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

# SECURITY
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-placeholder")
DEBUG = os.environ.get("DEBUG", "True") == "True"

# In production, set this properly:
ALLOWED_HOSTS = ["*", "frontendpython-djangobackend.onrender.com"]

# Custom user model
AUTH_USER_MODEL = 'analytics.User'

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Your app
    'analytics',

    # Third-party
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
]

# CORS (React frontend)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "https://frontendpython-djangobackend.onrender.com",
]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',  # must be near top
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL config
ROOT_URLCONF = 'population_site.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 👇 ADD THIS so Django can find your Vite index.html
         'DIRS': [os.path.join(BASE_DIR, 'population_site/static/frontend/dist')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'population_site.wsgi.application'

# Database (Supabase PostgreSQL)
DATABASES = {
     'default': {
        'ENGINE': 'mssql',
        'NAME': 'EventDrivenPopulationsDb',
        'USER': '',  # leave empty for trusted connection
        'PASSWORD': '',  # leave empty
        'HOST': 'localhost',
        'PORT': '',  # default port 1433 if empty
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'trusted_connection': 'yes',  # enables Windows Authentication
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 👇 ADD THESE — tells Django where to find Vite static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'population_site/static/frontend/dist'),
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login / logout redirects
LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = '/'

# DRF config
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
