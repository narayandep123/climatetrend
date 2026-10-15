from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-do-not-use-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in {'1', 'true', 'yes'}
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() in {'1', 'true', 'yes'}
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,https://localhost:5173,https://climatetrend-weld.vercel.app',
    ).split(',')
    if origin.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://.*\.vercel\.app$',
]
CSRF_TRUSTED_ORIGINS = [
    'https://climatetrend-weld.vercel.app',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'backend.app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.climate_project.urls'

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
APPEND_SLASH = False

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
