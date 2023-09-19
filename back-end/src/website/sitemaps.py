from blog.models import BlogPost
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from products.models import Category, Product


class BlogPostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return BlogPost.objects.all()

    def lastmod(self, obj):
        return obj.publish_date


class ProductSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return Product.objects.all()


class CategorySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return Category.objects.all()


class StaticViewSitemap(Sitemap):
    def items(self):
        return [
                "index"
                , "serenity"
                , "harrow"
                , "oxley"
                , "francisco"
                , "porscha"
                , "bathroom-planner"
                , "laundry-planner"
                , "video"
                , "subscribe"
                , "about-us"
                , "concept-showroom"
                , "vista-range"
        ]

    def location(self, item):
        return reverse(item)
