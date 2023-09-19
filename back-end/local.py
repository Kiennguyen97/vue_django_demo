import mimetypes

from website.config.settings import *

# INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["corsheaders.middleware.CorsMiddleware"]

INTERNAL_IPS = [
    "127.0.0.1",
]


mimetypes.add_type("application/javascript", ".js", True)
DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}




TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["src/website/templates/"],
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
    "default": {"USE_REDIS_CACHE": "default"},
    "low": {"USE_REDIS_CACHE": "low"},
}

# DEBUG=False

RECAPTCHA_SITE_KEY = "6LevdoglAAAAAEbpjA-F_2NZwBopRTraEqtK7wiq"
RECAPTCHA_SECRET_KEY = "6LevdoglAAAAAMDAdXQ8vETDvhcmCOCylbGju_Xs"



# Authentication settings
# The AWS region to connect to.
# AWS_REGION = "us-east-1"
#
# # The AWS access key to use.
# AWS_ACCESS_KEY_ID = "AKIA3GIDXR7TUC3K7AZT"
#
# # The AWS secret access key to use.
# AWS_SECRET_ACCESS_KEY = "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"
#
# # The optional AWS session token to use.
# #AWS_SESSION_TOKEN = ""
#
# # File storage settings
# # The name of the bucket to store files in.
# AWS_S3_BUCKET_NAME = "newtech-bucket"
# AWS_STORAGE_BUCKET_NAME = "newtech-bucket"
#
# # custom domain
# AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
# # ACL
# AWS_DEFAULT_ACL = 'public-read'
# # Cache age
# AWS_OBJECT_PARAMETERS = {
#     "CacheControl": "max-age=86400",
# }
#
# AWS_LOCATION = "static"
# AWS_LOCATION_MEDIA = "media"
# AWS_QUERYSTRING_AUTH = False
# AWS_HEADERS = {
#     "Access-Control-Allow-Origin": "*",
# }
#
# # Storages config for django >= 4.2
# STORAGES = {
#     "default": {
#         "BACKEND": "aws_storage.media_storage.MediaStorage"
#     },
#     "staticfiles": {
#         "BACKEND": "storages.backends.s3boto3.S3StaticStorage"
#     },
# }
#
# STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
# MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": os.environ["REDIS_URL"],
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         },
#     }
# }

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "amtech_web",
#         "USER": "",
#         "PASSWORD": "",
#         "HOST": "",
#         "POST": "",
#         "CONN_MAX_AGE": 600,
#     },
#     "TEST": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": os.path.join(BASE_DIR, "test_db.sqlite3"),
#     },
# }

# MEILISEARCH_URL=local
# MEILI_MASTER_KEY='test'

CSRF_TRUSTED_ORIGINS=['http://newtech-web.net', 'https://*']
CORS_ORIGIN_ALLOW_ALL = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost","newtech-web.net"]

CORS_ORIGIN_WHITELIST = [
    'http://newtech-web.net',
]

# Optional: Allow credentials in CORS requests
# Set this to True if you need to include cookies or authentication headers
CORS_ALLOW_CREDENTIALS = False