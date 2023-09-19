from rest_framework import serializers

from django.core.cache import cache
from django.db import models
from django.templatetags.static import static
from django.urls import reverse

from ckeditor.fields import RichTextField


# Create your models here.
class BlogPost(models.Model):
    class Meta:
        ordering = ["-publish_date"]

    title = models.CharField(max_length=255, unique=True)
    type_laundry = models.CharField(max_length=255, blank=True)
    author = models.CharField(max_length=255, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True)
    short_description = models.CharField(max_length=255, blank=True)
    body = RichTextField(blank=True, null=True)
    meta_description = models.CharField(max_length=150, blank=True)
    publish_date = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=True)
    image = models.FileField(upload_to="images/project/", blank=True)
    image_banner = models.FileField(upload_to="images/project/banner/", blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("project-details", args=(self.slug,))

    def get_img_url(self):
        return self.image.url

    def get_date_str(self):
        return self.publish_date.strftime("%d/%m/%Y")

    def get_dict(self):
        return self.__dict__

    @staticmethod
    def get_all_cached():
        """Gets cache, sets if empty"""
        blog_cache = cache.get("BLOG")
        if blog_cache:
            list_blogs = blog_cache["blogs"]
        if not blog_cache:
            list_blogs = []
            for item in BlogPost.objects.all():
                serializer = BlogPostSerializer(item).data
                list_blogs.append(serializer)
            blogs = {"blogs": list_blogs}
            cache.set("BLOG", blogs)
        return list_blogs


class PostImage(models.Model):
    post = models.ForeignKey(BlogPost, default=None, on_delete=models.SET_DEFAULT, related_name="additional_images")
    image = models.FileField(upload_to="images/project/post/", blank=True)

    def get_img_url(self):
        return self.image.url

    def __str__(self):
        return self.post.title

class BlogPostSerializer(serializers.ModelSerializer):
    get_absolute_url = serializers.CharField(read_only=True)
    get_img_url = serializers.SerializerMethodField()  # calls get_get_imgs_ursl below
    get_date_str = serializers.SerializerMethodField()  # calls get_get_imgs_ursl below

    class Meta:
        model = BlogPost

        fields = (
            "title",
            "type_laundry",
            "author",
            "subtitle",
            "slug",
            "short_description",
            "meta_description",
            "publish_date",
            "published",
            "get_absolute_url",
            "get_img_url",
            "get_date_str",
        )

    def get_get_img_url(self, blog):
        return blog.get_img_url()

    def get_get_date_str(self, blog):
        return blog.get_date_str()
