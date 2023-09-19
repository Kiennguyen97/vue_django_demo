import sentry_sdk
from ddtrace import config
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.rq import RqIntegration

from website.config.settings import *

INSTALLED_APPS.append("ddtrace.contrib.django")

config.django["trace_query_string"] = True
config.django["include_user_name"] = True
SECRET_KEY = os.environ["SECRET_KEY"]
CONFIG_ENV = CONFIG_ENVIRONS["prod"]
DEBUG = False
SECURE_HSTS_SECONDS = 120
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS=['https://pre-prod.newtech.co.nz','https://newtech.co.nz']

if not os.getenv("DISABLE_SENTRY"):
    ## add env var to disable sentry in interactive environment
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[DjangoIntegration(), RqIntegration()],
        environment=CONFIG_ENV,
        traces_sample_rate=0.05,
        send_default_pii=True,
    )

TEMPLATE_LOADERS = (
    (
        "django.template.loaders.cached.Loader",
        (
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ),
    ),
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PW"],
        "HOST": os.environ["DB_HOST"],
        "POST": os.environ["DB_PORT"],
        "CONN_MAX_AGE": 600,
    },
    "TEST": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "test_db.sqlite3"),
    },
}
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "low": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}
RQ_QUEUES = {
    "default": {"USE_REDIS_CACHE": "default", "DEFAULT_TIMEOUT": 600},
    "low": {"USE_REDIS_CACHE": "low", "DEFAULT_TIMEOUT": 600},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "stream": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["stream"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

BRAINTREE_GATEWAY = braintree.BraintreeGateway(
    braintree.Configuration(
        braintree.Environment.Production,
        merchant_id=os.environ["BRAINTREE_MERCHANT_ID"],
        public_key=os.environ["BRAINTREE_PUBLIC_KEY"],
        private_key=os.environ["BRAINTREE_PRIVATE_KEY"],
    )
)

"""
ODOO_CREDS = {
    "url": os.environ["ODOO_URL"],
    "db": os.environ["ODOO_DB"],
    "usr": os.environ["ODOO_USR"],
    "pw": os.environ["ODOO_PW"],
}
"""

DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]
SMTP_API_URL = os.environ["SMTP_API_URL"]
SMTP_API_KEY = os.environ["SMTP_API_KEY"]

EMAIL_CC = os.environ["ADMIN_EMAIL"]
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = os.environ["EMAIL_PORT"]
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = True
