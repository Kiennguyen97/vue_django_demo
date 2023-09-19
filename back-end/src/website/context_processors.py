import os

from cms.forms import SubscribeForm
from django.conf import settings
from products.models import Category
from products.models_cart import CartItem

from .breadcrumbs import get_crumbs


def export_vars(request):
    # cache_cat = Category.get_child_category_recurse_html()
    cart_count = CartItem.get_count(request)
    data = {
        "DJANGO_ENVIRON": settings.CONFIG_ENV,
        "BASE_URL": settings.BASE_URL,
        "STATIC_URL": settings.STATIC_URL,
        "MEDIA_DOCUMENT_ROOT": settings.MEDIA_DOCUMENT_ROOT,
        "CATEGORY_TREE_HTML": [],
        "CATEGORY_TREE_MB_HTML": [],
        "CATEGORY_TREE": Category.get_category_tree(),
        "CANONICAL_PATH": request.build_absolute_uri(request.path),
        "CRUMBS": get_crumbs(request),
        "RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY,
        "FORM_RECAPTCHA": settings.FORM_RECAPTCHA,
        "cls_subscribe_name": SubscribeForm().__class__.__name__,
        "cart_count": cart_count,
        "SENTRY_DSN": os.environ.get("SENTRY_DSN") if os.environ.get("SENTRY_DSN") else "",
        "ZENDESK_KEY": settings.ZENDESK_KEY,
        "GOOGLE_ANALYTICS": settings.GOOGLE_ANALYTICS,
        "GOOGLE_TAG_MANAGER": settings.GOOGLE_TAG_MANAGER,
    }
    return data
