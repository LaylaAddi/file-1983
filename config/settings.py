import os
from datetime import timedelta
from pathlib import Path
import dj_database_url
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Render terminates TLS at the load balancer; trust the forwarded header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'https://file1983.com',
    'https://www.file1983.com',
    'https://auditfile1983.com',
    'https://www.auditfile1983.com',
]

# Canonical domain. Any request to a non-canonical host (other than the Render
# *.onrender.com URL or localhost) is 301-redirected here by
# CanonicalDomainMiddleware. Used by templates for shareable links too.
PRIMARY_DOMAIN = config('PRIMARY_DOMAIN', default='auditfile1983.com')

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    # Stripe (and most webhook senders) do not follow 3xx responses, so any
    # http→https redirect on /stripe/webhook/ would silently lose events.
    # Exempting the path keeps webhook delivery resilient to misconfiguration.
    SECURE_REDIRECT_EXEMPT = [r'^stripe/webhook/?$']

AUTH_USER_MODEL = 'accounts.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'axes',

    # Local
    'accounts',
    'documents',
    'public_pages',
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
    'documents.middleware.CanonicalDomainMiddleware',
    'documents.middleware.CaptureReferralMiddleware',
    'accounts.middleware.RequireLegalAcceptanceMiddleware',
    # Must be last so it sees the final response/exception for every request.
    'axes.middleware.AxesMiddleware',
]

# django-axes checks this backend first; falls through to ModelBackend if the
# attempt isn't locked out.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Lock out after 5 failed attempts, combining username + IP so one bad actor
# can't lock out a shared NAT/office IP for everyone else.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_RESET_ON_SUCCESS = True

ROOT_URLCONF = 'config.urls'

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
                'config.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database — uses DATABASE_URL env var in prod, SQLite in dev
DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/documents/'
LOGOUT_REDIRECT_URL = '/'

# Email
# Default backend depends on DEBUG: prod uses SMTP (safe — fails loudly if
# misconfigured rather than leaking bodies into logs), dev uses console output.
# Override either with EMAIL_BACKEND env var.
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default=(
        'django.core.mail.backends.console.EmailBackend' if DEBUG
        else 'django.core.mail.backends.smtp.EmailBackend'
    ),
)
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=15, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@file1983.com')

# Stripe
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# Pricing — single document per purchase. Cents to avoid float math.
PRICE_FULL_CENTS = 14900       # $149.00 — list price
PRICE_DISCOUNTED_CENTS = 9900  # $99.00 — with valid promo code

# Referrer/partner cut as a percentage of each sale where their PromoCode was used.
# 20 -> referrer earns $19.80 on a $99 sale.
PARTNER_CUT_PERCENT = 20

# Minimum unpaid balance (in cents) a partner must have before they can submit
# a payout request from the dashboard. Avoids $0.40 trickle requests.
PARTNER_MIN_PAYOUT_CENTS = 2000  # $20.00

# Where partner payout-request notifications are sent. Falls back to
# DEFAULT_FROM_EMAIL if unset.
PARTNER_PAYOUT_NOTIFY_EMAIL = config(
    'PARTNER_PAYOUT_NOTIFY_EMAIL', default=''
) or config('DEFAULT_FROM_EMAIL', default='')

# AI quota per document. Counts story extraction + draft regeneration + addendums.
AI_QUOTA_FREE = 3       # Pre-payment AI calls allowed
AI_QUOTA_PAID = 150     # Post-payment AI calls (counter resets on payment)

# Free draft documents per user. Paid + finalized docs don't count toward this.
FREE_DOCS_PER_USER = 2

# Current version of Terms of Service and Privacy Policy. Bump when either
# document changes substantively to force every existing user to re-accept on
# next visit (RequireLegalAcceptanceMiddleware compares user's stored version
# against these). Also bump LegalDocument.version in admin so the displayed
# version label matches.
TOS_VERSION = config('TOS_VERSION', default='v1')
PRIVACY_VERSION = config('PRIVACY_VERSION', default='v1')

# OpenAI
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Supadata
SUPADATA_API_KEY = config('SUPADATA_API_KEY', default='')

# REST Framework + JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# Admin URL — set ADMIN_URL env var on Render to something secret
ADMIN_URL = config('ADMIN_URL', default='manage-dev/')

# Logging — surface 500 tracebacks to stderr so they show up in Render logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'documents': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
