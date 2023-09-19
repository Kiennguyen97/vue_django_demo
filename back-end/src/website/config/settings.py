import os
from cgi import test
from logging.config import dictConfig
from pathlib import Path

import braintree

from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "secret"
AUTH_USER_MODEL = "customers.CustomUser"

## just to ensure you've got something loaded in
CONFIG_ENVIRONS = {"dev": "dev", "test": "test", "prod": "prod"}
CONFIG_ENV = CONFIG_ENVIRONS["dev"]

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost","newtech-web.net"]

if os.getenv("ALLOWED_HOST"):
    ALLOWED_HOSTS.extend(os.environ["ALLOWED_HOST"].split(","))

INSTALLED_APPS = [
    "django.contrib.humanize",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "rest_framework",
    "django_extensions",
    "ckeditor",
    "django_rq",
    "products",
    "blog",
    "cms",
    "customers",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "crum.CurrentRequestUserMiddleware",
    "website.breadcrumbs.CrumbsMiddleware",
    "customers.middleware.CustomersMiddleware",
    "website.middleware.GeneralMiddleware",
]


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
    # 'default': {
    #     'BACKEND': 'django_redis.cache.RedisCache',
    #     'LOCATION': os.environ['REDIS_URL'],
    #     'OPTIONS': {
    #         'CLIENT_CLASS': 'django_redis.client.DefaultClient',
    #     }
    # }
}

RQ_QUEUES = {
    "default": {"HOST": "localhost", "PORT": 6379, "DB": 0, "DEFAULT_TIMEOUT": 360},
    "low": {"HOST": "localhost", "PORT": 6379, "DB": 0, "DEFAULT_TIMEOUT": 360},
}


ROOT_URLCONF = "website.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["website/templates/"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "website.context_processors.export_vars",
            ],
        },
    },
]

WSGI_APPLICATION = "website.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Pacific/Auckland"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = os.getenv("STATIC_URL", "static/") ## static/ in dev, CDN in prod

## where staticfiles are found (dev only)
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

## where collectstatic collects to
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

BASE_URL = os.getenv("BASE_URL", "localhost")

MEDIA_URL = "/media/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_DOCUMENT_ROOT = os.getenv("MEDIA_DOCUMENT_ROOT", "/tmp/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

#### app settings, probably should be somewhere else
MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

# sandbox BT keys
BRAINTREE_GATEWAY = braintree.BraintreeGateway(
    braintree.Configuration(
        braintree.Environment.Sandbox,
        merchant_id="2h24g2jjx6zy6bgq",
        public_key="cq3r6dcx8yf78b8k",
        private_key="3d443f10f3ab5dbb781df2c095982825",
    )
)

GST_RATE = 0.15
BANK_ACCOUNT = "12-3211-0002851-00"
EMAIL_NO_REPLY = "no-reply@newtech.co.nz"

ADMINS = [("Mitchell", "mitchell@amtech.co.nz")]
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "admin@example.com")
EMAIL_CC = os.getenv("ADMIN_EMAIL", "admin@example.com")
SMTP_API_URL = os.getenv("SMTP_API_URL", "https://devnull-as-a-service.com/dev/null")
SMTP_API_KEY = os.getenv("SMTP_API_KEY", "keys-123s")

EMAIL_BCC = []

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


## recaptcha admin console is under mitchell@amtech.co.nz
RECAPTCHA_SITE_KEY = "6LdliMslAAAAAH5rDqJbCLUxRGwlXZt-CIMoWqCz"
RECAPTCHA_SECRET_KEY = "6LdliMslAAAAAKYfDw2rcYJjrRfPi253Kq39bU2a"
RECAPTCHA_API = "https://www.google.com/recaptcha/api/siteverify"

FORM_RECAPTCHA = [
    "ContactForm",
    "SingInForm",
    "RegisterForm",
    "SubscribeForm",
    "RegisterFromInvitationForm",
    "CheckoutForm",
    "UniversalForm",
]

MEILI_INDEDX = os.getenv("MEILI_INDEDX", "products")
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "")
MEILISEARCH_URL = os.getenv("MEILISEARCH_URL", "http://localhost:7702")

DEFAULT_SALES_PERSON = {"name": "Customer Service Team", "email": "sales@newtech.co.nz"}
# DEFAULT_SALES_PERSON = {"name": "Customer Service Team", "email": "sales@amtech.co.nz"}
# ADDRESSRIGHT_API_ENPOIN = "https://addressright.co.nz"
# ADDRESSRIGHT_API_KEY = "337676_4xM15WXZVq1zldiL"

XML_FIELD = "google_merchant_feed.xml"
XML_FORMAT = "rss"
EXCLUDE_CAT_IDS = []
INCLUDE_CAT_IDS = []

CLOUDFRONT_KEY_PATH = os.getenv("CLOUDFRONT_KEY_PATH", "")
CLOUDFRONT_KEY_ID = os.getenv("CLOUDFRONT_KEY_ID", "")
CATEGORY_ID="cb9f669e-52aa-4efa-bba4-8f0ff3e28680"
ZENDESK_KEY="4053a4bf-bf4b-4daa-9acb-b4424796d88b"
CSRF_TRUSTED_ORIGINS=['http://*', 'https://*']

CREDIT_CARD_SURCHARGE = (0.00, "0.00%")

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

GOOGLE_ANALYTICS = "G-X0ZR1Y8NWW"
GOOGLE_TAG_MANAGER = "GTM-5KP6C22"

