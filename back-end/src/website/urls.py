from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic.base import TemplateView

from .sitemaps import BlogPostSitemap, ProductSitemap, StaticViewSitemap

robots_file = "robots.txt" if settings.CONFIG_ENV == "prod" else "robots-test.txt"

sitemaps = {
    "blogpost": BlogPostSitemap,
    "products": ProductSitemap,
    "static": StaticViewSitemap,
}

from blog.models import BlogPost

urlpatterns = [
    path("", include("cms.urls")),
    path("projects/", include("blog.urls")),
    path("customers/", include("customers.urls")),
    path(
        "robots.txt",
        TemplateView.as_view(template_name=robots_file, content_type="text/plain"),
    ),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # path("website_admin/", admin.site.urls),
    re_path(r"^website_admin/?", admin.site.urls),
    path("", include("products.urls")),
]

if settings.CONFIG_ENV == "dev":
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
