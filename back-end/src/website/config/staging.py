from website.config.settings import *
from decouple import config

SECRET_KEY = os.environ["SECRET_KEY"]


CONFIG_ENV = CONFIG_ENVIRONS["test"]
DEBUG = False


CSRF_TRUSTED_ORIGINS=['https://test-site.newtech.co.nz']
ALLOWED_HOSTS += 'test-site.newtech.co.nz'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PW"),
        "HOST": config("DB_HOST"),
        "POST": config("DB_PORT"),
        "CONN_MAX_AGE": 600,
    },
    "TEST": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "test_db.sqlite3"),
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "low": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}
RQ_QUEUES = {
    "default": {"USE_REDIS_CACHE": "default"},
    "low": {"USE_REDIS_CACHE": "low"},
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
