from django.contrib import admin
 
from .models import BlogPost, PostImage
 
class PostImageAdmin(admin.TabularInline):
    model = PostImage
    extra = 0
    save_as = True
 
@admin.register(BlogPost)
class PostAdmin(admin.ModelAdmin):
    inlines = [PostImageAdmin]
 
    class Meta:
       model = BlogPost
 
# @admin.register(PostImage)
# class PostImageAdmin(admin.ModelAdmin):
#     pass