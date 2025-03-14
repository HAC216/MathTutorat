from pathlib import Path
import os
import environ

# Initialisation de django-environ
env = environ.Env()

# Chargement du fichier .env si disponible
if os.path.exists(Path(__file__).resolve().parent.parent / ".env"):
    environ.Env.read_env(Path(__file__).resolve().parent.parent / ".env")

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = env('SECRET_KEY', default='change-me-in-production')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'gestion_tutorat'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Ajouté ici
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# URL configuration
ROOT_URLCONF = 'MathTutorat.urls'

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'MATHTUTORAT',
        'USER': 'postgres',
        'PASSWORD': 'passer',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
import dj_database_url

# Remplacer la configuration par l'URL de la base de données Render si disponible
DATABASE_URL = env('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)
    DATABASES['default']['CONN_MAX_AGE'] = 600
    # Configuration SSL pour Render
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

AUTH_USER_MODEL = 'gestion_tutorat.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'gestion_tutorat.EmailBackend.EmailBackend',
]

# WSGI application
WSGI_APPLICATION = 'MathTutorat.wsgi.application'

# Authentication password validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Localization
LANGUAGE_CODE = 'fr-FR'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files settings
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # Pour collectstatic en production

# Default primary key type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Configuration pour les alertes
ALERT_ADMIN_EMAIL = env('ALERT_ADMIN_EMAIL', default='')
SITE_NAME = env('SITE_NAME', default='')
ALERT_EMAILS_ENABLED = env('ALERT_EMAILS_ENABLED', default='')

if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    print("⚠️  Attention : EMAIL_HOST_USER ou EMAIL_HOST_PASSWORD non définis !")

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')