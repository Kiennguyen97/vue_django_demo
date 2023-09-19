import json
import math
import os
from dataclasses import dataclass
from urllib.parse import urlencode

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.account import Page
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, render
from website.breadcrumbs import add_crumbs
from blog.models import BlogPost

from .models import Category, Product, ProductSerializer
from .serializers import CartItemSerializer
from .utils import inject_cls
from django.conf import settings
from django.http import Http404


#TODO: remove this when have data
def vanities_by_type(request, **kwargs):
    return render(request, "vanities-by-type.html")

def vanities_by_type_wall_hung(request, **kwargs):
    return render(request, "vanities-by-type-wall-hung.html")

#########################
## below is code used from amtech, may not be relevant
########################


###product sort options
@dataclass
class ProductSortOptions:  ## non django managed model
    name: str
    slug_name: str
    sort_method: str


SORT_OPTIONS = [
    ProductSortOptions(name="Default", slug_name="default", sort_method="-ordering"),
    # ProductSortOptions(name="Featured Items", slug_name="featured", sort_method="featured"),
    # ProductSortOptions(name="Newest Items", slug_name="newest", sort_method="-created_at"),
    # ProductSortOptions(name="Best Selling", slug_name="best-selling", sort_method="best-selling"),
    ProductSortOptions(name="A to Z", slug_name="name-a-z", sort_method="name"),
    ProductSortOptions(name="Z to A", slug_name="name-z-a", sort_method="-name"),
    # ProductSortOptions(name="By Review", slug_name="by-review", sort_method="by-review"),
    ProductSortOptions(name="Price: Ascending", slug_name="price-low-high", sort_method="list_price"),
    ProductSortOptions(name="Price: Descending", slug_name="price-high-low", sort_method="-list_price"),
]

SORT_OPTIONS_NEWS = [
    ProductSortOptions(name="Relevance", slug_name="relevance", sort_method=""),
    ProductSortOptions(name="A to Z", slug_name="name-a-z", sort_method="title"),
    ProductSortOptions(name="Z to A", slug_name="name-z-a", sort_method="-title"),
]

NEW_FIELDS = [
    'title',
    'body',
    'slug',
]

SORT_OPTIONS_DICT = {x.slug_name: x for x in SORT_OPTIONS}
SORT_OPTIONS_NEWS_DICT = {x.slug_name: x for x in SORT_OPTIONS_NEWS}

def get_sort_options():
    sort_options = []
    sort_options_news = []
    for opt in SORT_OPTIONS:
        sort_options.append(
            {
                "value": opt.sort_method,
                "label": opt.name,
            }
        )
    for opt in SORT_OPTIONS_NEWS:
        sort_options_news.append(
            {
                "value": opt.sort_method,
                "label": opt.name,
            }
        )
    return sort_options, sort_options_news

def page_laundry(request,**kwargs):
    
    cat = Category.objects.get(uuid=settings.CATEGORY_ID)
    products = cat.get_all_descendant_prods()
    context = {
        "category": cat,
        "products": products
    }
    return render(request, "laundry.html", context)


def product_category(request,**kwargs):
    """used for returning base products grid,
    or products grid page for a category, depending on
    the kwargs"""
    ## need to reimplment this now
    order = "default"
    if request.GET.get("sort"):
        order = request.GET["sort"]
        assert order in SORT_OPTIONS_DICT.keys()

    slug = kwargs.get("category_path")
    search_term = request.GET.get("q")
    cat = None
    number_item = 24
    sort_options, sort_options_news = get_sort_options()

    context_list= {
        "csrf_token": get_token(request),
        "sort_options": sort_options,
        "sort_options_news": sort_options_news,
        "number_item": number_item,
        "is_search": True if search_term else False,
    }

    if slug:
        # is to view a category page
        slugs = kwargs.get("category_path").split("/")
        slug = slugs[-1] if slugs[-1] else slugs[-2]
        try:
            cat = Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            raise Http404("Category does not exist")

        page_type = "CATEGORY_VIEW"
        add_crumbs(request, cat.get_breadcrumbs())
        context_list["uuid"] = cat.uuid
    elif search_term:
        # is to view a search page
        page_type = "SEARCH_VIEW"
        context_list["uuid"] = search_term
        request._crumbs = [{"name": "Search", "link": None}]
    else:
        # viewing highest level category
        cat = Category.objects.filter(category_level__exact=0).first()
        page_type = "CATEGORY_VIEW"
        add_crumbs(request, cat.get_breadcrumbs())
        context_list["uuid"] = cat.uuid

    context_list["page_type"] = page_type
    context = {
        "category": cat,
        "search_term": search_term,
        "config": context_list,
        "page_title": cat.name if page_type == "CATEGORY_VIEW" else "Newtech | Innovative Bathroomware Products & Design in New Zealand"
    }
    

    return render(request, "list-product.html", context)


@api_view(["POST"])
def product_category_reload(request):
    """
    Frontend calls this to get all the product info
    Called from category, search, and brand pages
    """

    context = {}

    cls_name = request.headers["Class-Name"]
    assert cls_name in ["BRAND_VIEW", "CATEGORY_VIEW", "SEARCH_VIEW"]

    post_data = request.data
    number_item = int(post_data.get("number_item"))
    page_number = int(post_data.get("page_number"))
    kwargs = {
        "request": request,
        "data": post_data,
    }

    class_up = inject_cls.get_cls(cls_name)()
    number_per_page = class_up.per_page
    results = class_up.get_context_data(**kwargs)
    products = results["products"]
    paginator = Paginator(products, number_item)
    page_obj = paginator.get_page(page_number)

    page_ranges = []


    # if post_data.get("is_search"):
        # TODO: get news from blog posts from body follow NEW_FIELDS
        # blog_kwargs = {
        #     'search_term': post_data.get("uuid"),
        #     'order': post_data.get("ordering_news"),
        #     'list_fields': NEW_FIELDS,
        # }
        # news = list(BlogPost.search_blog(**blog_kwargs))
        # context.update({"news": news})

    page_ranges = []
    for i in page_obj.paginator.page_range:
        page_ranges.append(i)

    pagination = {
        "has_previous": page_obj.has_previous(),
        "previous_page_number": page_obj.previous_page_number()
        if page_obj.has_previous()
        else 0,
        "has_next": page_obj.has_next(),
        "next_page_number": page_obj.next_page_number() if page_obj.has_next() else 0,
        "number": page_obj.number,
        "previous_hellip": int(page_obj.number) - 4,
        "num_pages": page_obj.paginator.num_pages,
        "next_hellip": int(page_obj.number) + 4,
        "page_ranges": page_ranges,
        "number_previous_hellip": int(page_obj.number) - 5,
        "number_next_hellip": int(page_obj.number) + 5,
    }

    if post_data.get("first"):
        context.update({
            "items": class_up.get_product_data(page_obj),
            "pagination": pagination,
            "childs": results["child_list"],
        })
    else:
        context.update({
            "items": class_up.get_product_data(page_obj),
            "pagination": pagination,
        })


    return Response(context)
