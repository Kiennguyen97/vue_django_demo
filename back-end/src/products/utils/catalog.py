import json
import math
import os
from datetime import datetime as dt

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.db.models.expressions import Case, F, OuterRef, Subquery, When
from django.templatetags.static import static
from django.urls import reverse

from .inject import Inject


class BaseProductList:
    def __init__(self):
        self.per_page = 24
        self.child_list = []
        self.products = []
        self.results = {}
        self.total_hits = 0;
        self.total_pages = 0;

    def get_product_data(self, products):
        items = []
        for obj in products:
            item = {
                "name": obj.name,
                "sku": obj.get_product_sku(),
                "slug": obj.get_absolute_url(),
                "min_price": obj.get_price(),
                "max_price": obj.get_max_price(),
                "image_urls": obj.get_image_hi_res_urls(),
                "number_total": obj.get_number_option(),
                "can_purchase": obj.check_can_purchase(),
            }
            items.append(item)
        return items

    def process(self, request_data, *args, **kwargs):
        pass

    def get_request_data(self, *args, **kwargs):
        data = kwargs["data"]
        context = {
            "page_number": data["page_number"],
            "uuid": data["uuid"],
            "first": data["first"],
            "ordering": data["ordering"],
        }
        return context

    def get_context_data(self, *args, **kwargs):
        request_data = self.get_request_data(*args, **kwargs)
        self.process(request_data, *args, **kwargs)
        return self.results


@Inject.register_cls
class ProductList(BaseProductList):
    cls_name = "CATEGORY_VIEW"

    def process(self, request_data, *args, **kwargs):
        from products.models import Category
        cat = Category.objects.get(uuid=request_data["uuid"])
        if request_data.get("first"):
            child_list = cat.child_category_list.all()
            for child in child_list:
                cat_slug = child.get_absolute_url()
                slug = reverse("category-grid", kwargs={"category_path": cat_slug})
                item = {
                    "name": child.name,
                    "slug": slug
                }
                self.child_list.append(item)
            self.results["child_list"] = self.child_list

        self.products = cat.get_all_descendant_prods(order=request_data['ordering'])
        self.results["products"] = self.products

@Inject.register_cls
class Search(BaseProductList):
    cls_name = "SEARCH_VIEW"

    def process(self, request_data, *args, **kwargs):
        from products.search import make_search
        from products.models import Product
        product_skus = make_search(request_data["uuid"])
        products = Product.objects.filter(sku__in=product_skus)

        # TODO: Add advance search
        # advance_search = kwargs.get('data')['advance_search']
        # if advance_search:
        #     """
        #     filter by price
        #     filter by is_featured 1 is only featured 2 is not featured
        #     filter by is_free_shipping 1 is only free shipping 2 is not free shipping
        #     """
        #     price_to = advance_search.get('price_to')
        #     price_from = advance_search.get('price_from') if advance_search.get('price_from') else 0
        #     is_featured = True if advance_search.get('is_featured') == '1' else False
        #     is_free_shipping = True if advance_search.get('is_free_shipping') == '1' else False
        #     if price_to:
        #         self.products = self.products.filter(list_price__gte=price_from, list_price__lte=price_to)
        #     if advance_search.get('is_featured'):
        #         self.products = self.products.filter(is_featured=is_featured)
        #     if advance_search.get('is_free_shipping'):
        #         self.products = self.products.filter(is_free_shipping=is_free_shipping)



        if request_data['ordering'] in ["ordering", "-ordering"]:
            product_ordering = {key: i for i, key in enumerate(product_skus)}
            products = sorted(products, key=lambda x: product_ordering.get(x.sku, 9999))
            self.products = products
        else:
            self.products = products.order_by(request_data['ordering'])
        
        if request_data.get("first"):
            # child_list = list(map(lambda x: x.category_id, self.products))
            # print(child_list)
            # for child in child_list:
            #     item = {
            #         "name": child.name,
            #         "slug": child.get_absolute_url()
            #     }
            #     self.child_list.append(item)
            self.results["child_list"] = self.child_list

        self.results["products"] = self.products

@Inject.register_cls
class Brand(BaseProductList):
    cls_name = "BRAND_VIEW"

inject_cls = Inject()
