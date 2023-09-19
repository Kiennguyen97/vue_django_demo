import json
import os
import uuid
import itertools
from datetime import date, datetime, timedelta

from ckeditor.fields import RichTextField
from crum import get_current_user

# from embed_video.fields import EmbedVideoField
from rest_framework import serializers
# Non-field imports, but public API
from rest_framework.fields import empty

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q, Sum
from django.db.models.expressions import Case, F, OuterRef, Subquery, When
from django.templatetags.static import static
from django.utils.functional import cached_property

# from .models_lists import PricelistCustomerRel, PricelistItem
# from .utils import check_closed_purchase_by_user_and_product
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.urls import reverse


CATEGORY_BREADCRUMBS_LIST = "CATEGORY_BREADCRUMBS_LIST"
PRODUCT_BREADCRUMBS = "PRODUCT_BREADCRUMBS"
CATEGORY_BREADCRUMBS = "CATEGORY_BREADCRUMBS"


def gen_user_prefix(user):
    if user is None or not user.is_authenticated:
        prefix = "ANON"
    elif user.get_group_code() == "TRADE":
        prefix = user.company_id.uuid
    else:
        prefix = "RETAIL"

    return "BLOCK#" + prefix


def generate_combinations_recursive(array, current_index=0):
    if current_index >= len(array):
        return []

    current_sublist = array[current_index]
    remaining_combinations = generate_combinations_recursive(array, current_index + 1)
    combinations = []

    for value in current_sublist:
        combinations.append(value)
        combinations.extend([value + " " + combo for combo in remaining_combinations])

    return combinations

def get_placeholder_image():
    try:
        placeholder_img = static("img/home-new/placeholder.png")
    except Exception as e:
        placeholder_img = f"{settings.STATIC_URL}img/home-new/placeholder.png"
    return placeholder_img

class Category(models.Model):
    PLACEHOLDER_IMG = get_placeholder_image()

    class Meta:
        ordering = [
            "ordering",
        ]

    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=200)
    parent_category = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="child_category_list",
        blank=True,
        null=True,
    )
    slug = models.SlugField(max_length=255, unique=True)
    title = RichTextField(max_length=255, blank=True)
    # image_url = models.CharField(max_length=100, blank=True)
    # image_url = models.ImageField(upload_to='images/categories/', blank=True, null=True)
    image_url = models.FileField(upload_to="images/categories/", blank=True, null=True)
    meta_title = models.CharField(max_length=250, blank=True)
    meta_description = models.CharField(max_length=250, blank=True)
    # odoo_id = models.IntegerField()
    hide_on_web = models.BooleanField(default=False)
    show_logo = models.BooleanField(default=False)
    # view_type = models.CharField(max_length=100, blank=True, null=True)
    ordering = models.PositiveIntegerField(default=0)
    resource = RichTextField(blank=True, null=True)

    def __str__(self):
        return self.full_display()

    def get_template(self):
        return self.view_type

    def get_img_url(self):
        image_urls = []
        if self.image_url == "":
            return self.PLACEHOLDER_IMG
        else:
            image_urls.append(self.image_url.url)
        return image_urls[0]

    def get_descendant_cats(self):
        """Gets all descendent cats (including self)
        Arbitrarily gets 3 levels deep"""
        cat_cache = cache.get("CATEGORY" + self.uuid)
        if cat_cache:
            cats = cat_cache["cats"]
        if not cat_cache:
            cats = [self.uuid]
            this_lvl_cats = [self.uuid]
            while Category.objects.filter(parent_category__in=this_lvl_cats).exists():
                this_lvl_cats = list(
                    Category.objects.filter(parent_category__in=this_lvl_cats).values_list(
                        "uuid", flat=True
                    )
                )
                cats.extend(this_lvl_cats)

            cache.set("CATEGORY" + self.uuid, {"cats": cats})
        return cats

    def get_all_descendant_prods(self, order="default"):
        # catprod = Product.objects.filter(category__in=self.get_descendant_cats()).distinct()
        catprod = Product.objects.filter(categories__in=self.get_descendant_cats()).distinct()

        if order != "default":
            return catprod.order_by(order)
        return catprod

    def full_display(self):
        str = self.name
        parent_category_obj = self.parent_category
        while parent_category_obj is not None:
            str = parent_category_obj.name + " / " + str
            parent_category_obj = parent_category_obj.parent_category
        return str

    def get_absolute_url(self):

        if url := cache.get("CATEGORY_URL" + self.uuid):
            return url
        else:
            str_slug = self.slug
            parent_category_obj = self.parent_category
            while parent_category_obj is not None:
                if parent_category_obj.parent_category_id is not None:
                    str_slug = parent_category_obj.slug + "/" + str_slug
                parent_category_obj = parent_category_obj.parent_category
            cache.set("CATEGORY_URL" + self.uuid, f"{str_slug}")
            return f"{str_slug}"

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(Category, self).save(*args, **kwargs)

    @staticmethod
    def get_top_level():
        if cat := cache.get("TOP_LEVEL_CAT"):
            pass
        else:
            cat = Category.objects.filter(parent_category__isnull=True).first()
            cache.set("TOP_LEVEL_CAT", cat)
        return cat

    @staticmethod
    def get_category_tree():
        ## currently returns all categories
        ## should be serialised and put to cache at some point
        if category_tree := cache.get("CATEGORY_TREE"):
            pass
        else:
            category_tree = []
            base_cat = Category.get_top_level()
            if base_cat:
                # base_cat_slug = base_cat.get_absolute_url()

                cats_lv1_objs = Category.objects.select_related("parent_category").filter(
                    parent_category__uuid=base_cat.uuid
                )
                cats_lv2_objs = Category.objects.select_related("parent_category").filter(
                    parent_category__uuid__in=cats_lv1_objs.values("uuid")
                )

                items = {}
                for cat in cats_lv2_objs:
                    parent_uuid = cat.parent_category.uuid
                    if items.get(parent_uuid):
                        items[parent_uuid].append(cat)
                    else:
                        items[parent_uuid] = [cat]

                for cat_top in cats_lv1_objs:
                    cat_uuid = cat_top.uuid
                    cat_slug = f"{cat_top.slug}"
                    slug = reverse("category-grid", kwargs={"category_path": cat_slug})
                    tree = {
                        "uuid": cat_top.uuid,
                        "name": cat_top.name,
                        "slug": slug,
                        "children": [],
                        "has_children": False,
                    }
                    if items.get(cat_uuid):
                        for item in items[cat_uuid]:
                            cat_lv2_slug = f"{cat_slug}/{item.slug}"
                            slug_lv2 = reverse("category-grid", kwargs={"category_path": cat_lv2_slug})
                            children_item = {
                                "uuid": cat_top.uuid,
                                "name": item.name,
                                "slug": slug_lv2,
                                "children": [],
                            }
                            tree["children"].append(children_item)
                        tree["has_children"] = True

                    category_tree.append(tree)
            cache.set("CATEGORY_TREE", category_tree)
        return category_tree

    def get_breadcrumbs(self):
        cache_key = CATEGORY_BREADCRUMBS + self.uuid
        if items := cache.get(cache_key):
            pass
        else:
            items = self.get_list_breadcrumbs()
            items = reversed(items)
            cache.set(cache_key, items)
        return items

    def get_list_breadcrumbs(self, get_list=False):
        items = []
        cache_key = CATEGORY_BREADCRUMBS_LIST + self.uuid
        if cache.get(cache_key):
            items = cache.get(cache_key)
            if get_list:
                items[0]["link"] = reverse("category-grid", kwargs={"category_path": self.get_absolute_url()})
        else:
            cat = self
            while cat is not None and cat.name != "Web":
                slug = cat.get_absolute_url()
                items.append(
                    {
                        "name": cat.name,
                        "link": reverse("category-grid", kwargs={"category_path": slug}),
                    }
                )
                cat = cat.parent_category
            cache.set(cache_key, items)
        return items

    def get_resource_html(self):
        if self.resource:
            return mark_safe(self.resource)
        return ""

    def get_title(self):
        if self.title:
            return mark_safe(self.title)
        return mark_safe(self.name)


### PRODUCT
class ProductAccessManager(models.Manager):
    def get_queryset(self):
        user = get_current_user()
        product_queryset = super().get_queryset()
        if user is not None and user.id and user.is_superuser:
            return product_queryset
        else:
            prod_option_relate = (
                ProductOptionRel.objects.select_related("product")
                .annotate(
                    option_prce=Subquery(
                        Option.objects.filter(productoption_id=OuterRef("productoption_id"))
                        .order_by("-price_adjust")
                        .values("price_adjust")[:1]
                    )
                )
                .values("product__sku")
                .annotate(total_price=Sum("option_prce"), number_total=Count("product__sku"))
                .distinct()
            )
            product_queryset = product_queryset.annotate(
                total_price=Subquery(
                    prod_option_relate.filter(product__sku=OuterRef("sku"))
                    .order_by("-total_price")
                    .values("total_price")[:1]
                ),
                number_total=Subquery(
                    prod_option_relate.filter(product__sku=OuterRef("sku"))
                    .order_by("-number_total")
                    .values("number_total")[:1]
                )
            )
            return product_queryset.filter(active=True)


def get_combination(array):
    if len(array) == 0:
        return []
    if len(array) == 1:
        return array[0]
    else:
        return [x + ' ' + y for x in array[0] for y in get_combination(array[1:])]

class Product(models.Model):
    PLACEHOLDER_IMG = get_placeholder_image()

    class Meta:
        ordering = [
            "-ordering",
        ]

    class ACCESS_LEVEL(models.TextChoices):
        OPEN = ("OPEN", "Public")  ## anyone can access, publicly
        LOGIN = ("LOGIN", "Logged In")  ## customers logged in
        TRADE = ("TRADE", "Trade Customers")  ## customers with trade acc only
        CLOSED = ("CLOSED", "Closed Purchase")  ## Customers with specific access

    class AVAILABILITY(models.TextChoices):
        IN_STOCK = ("IN_STOCK", "In Stock")
        LOW_STOCK = ("LOW_STOCK", "Low Stock")
        OUT_OF_STOCK = ("OUT_OF_STOCK", "Out of stock")

    class STOCKTYPE(models.TextChoices):
        STOCKED_ITEM = ("STOCKED_ITEM", "Stocked Item")
        INDENT_ITEM_LOCAL = ("INDENT_ITEM_LOCAL", "Indent Item - Local")
        INDENT_ITEM_OVERSEAS = ("INDENT_ITEM_OVERSEAS", "Indent Item - Overseas")
        MANUFACTURED_ITEM = ("MANUFACTURED_ITEM", "Manufactured Item")

    objects = ProductAccessManager()  # access for active prods, per user
    # all_objects = models.Manager()  # every product ever, no access check

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=256, unique=True)

    sku = models.CharField(max_length=100, unique=True, primary_key=True, default=uuid.uuid4)
    # TODO:TASK2511 new field for product code
    code = models.CharField(max_length=100, null=True, blank=True, unique=True)
    description_short = models.CharField(max_length=200, null=True)

    description_long = RichTextField(blank=True, null=True)
    meta_description = models.CharField(max_length=350, blank=True, null=True)
    # image_urls = models.CharField(max_length=1000, null=True)
    # image_hover = models.CharField(max_length=1000, null=True)
    image_hover = models.FileField(upload_to="images/products/", null=True, blank=True)
    website_template = models.CharField(max_length=100, blank=True, null=True)

    # retail_price = models.DecimalField(max_digits=7, decimal_places=2)
    list_price = models.DecimalField(max_digits=12, decimal_places=2)

    active = models.BooleanField(default=True)
    can_purchase = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_free_shipping = models.BooleanField(default=False)

    delivery_timeframe = models.CharField(max_length=45, blank=True)
    category = models.ForeignKey(
        "products.Category", on_delete=models.SET_NULL, null=True, blank=True
    )

    categories = models.ManyToManyField(Category, blank=True, related_name="categories_all")

    file_download_link = models.CharField(max_length=100, blank=True)
    file_download_image = models.CharField(max_length=100, blank=True)
    # access_view = models.CharField(choices=ACCESS_LEVEL.choices, max_length=15, default="OPEN")
    # access_purchase = models.CharField(choices=ACCESS_LEVEL.choices, max_length=15, default="OPEN")

    meta_keywords = models.CharField(max_length=250, blank=True, null=True)
    # brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    ordering = models.PositiveIntegerField(default=0)

    # availability = models.CharField(choices=AVAILABILITY.choices, max_length=25, default="IN_STOCK")
    # resource_urls = RichTextField(blank=True, null=True)

    dimension = models.CharField(max_length=100, null=True, blank=True)

    options = models.ManyToManyField(
        "products.ProductOption", through="ProductOptionRel", related_name="options_all"
    )

    resources = models.ManyToManyField(
        "products.ProductResource", through="ProductResourceRel", related_name="resources_all"
    )

    groups = models.ManyToManyField(
        "products.GroupProduct", through="GroupProductRel", related_name="groups_all"
    )

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = str(uuid.uuid4())
        super(Product, self).save(*args, **kwargs)
        # TODO TASK2713: Update Search Index
        from .meili_search import client

        try:
            client.get_index(settings.MEILI_INDEDX)
        except Exception as e:
            client.create_index()

        try:
            client.reindex_add_by_ids([self.sku])
        except:
            pass
        # END TODO TASK2713


    @property
    def get_sku_additions(self): 
        sku_additions = []
        option_queryset = Option.objects.select_related("productoption").filter(
            productoption__id__in=self.options.through.objects.filter(product=self).values("productoption_id"),
            sku_addition__isnull=False
        )
        if option_queryset.count():
            for o in option_queryset.all():
                sku_additions.append(o.sku_addition)
        return sku_additions

    def __str__(self):
        if self.get_product_sku() == '':
            return self.name
        else:
            return self.get_product_sku() + " - " + self.name

    def get_name(self):
        import html
        return html.escape(self.name)

    def get_active_status(self):
        return self.active

    def get_absolute_url(self):
        return reverse("product-detail", kwargs={"slug": self.slug})

    def get_brand(self):
        if self.brand and self.brand.name:
            return self.brand.name
        return ""

    def get_product_same_group(self):
        products = []
        if self.groups.all().count():
            for group in self.groups.all():
                products.extend(group.products.all())
        return products

    @classmethod
    def get_best_sellers(self):
        return []

    @classmethod
    def get_featured_products(self):
        featured_products = Product.objects.filter(active=True, is_featured=True)
        return featured_products[:4]

    # def get_img_urls(self):
    #     if self.image_urls == "" or self.image_hi_res == None:
    #         return [Product.PLACEHOLDER_IMG]
    #
    #     if settings.CONFIG_ENV == "dev":
    #         if os.getenv("IMG_URL"):
    #             return [
    #                 f"{os.getenv('IMG_URL')}/filestore/{x.strip()}"
    #                 for x in self.image_urls.split(",")
    #             ]
    #         else:
    #             return [static(f"/img/product/{x.strip()}") for x in self.image_urls.split(",")]
    #     else:
    #         return [static(f"filestore/{x}") for x in self.image_urls.split(",")]

    # def get_image_hover_urls(self):
    #     if self.image_hover == "" or self.image_hover == None:
    #         return self.get_img_urls()
    #
    #     if settings.CONFIG_ENV == "dev":
    #         if os.getenv("IMG_URL"):  ## put in IMG_URL for live site to see all the imgs in dev
    #             return [
    #                 f"{os.getenv('IMG_URL')}/filestore/{x.strip()}"
    #                 for x in self.image_hover.split(",")
    #             ]
    #         else:
    #             return [static(f"/img/product/{x.strip()}") for x in self.image_hover.split(",")]
    #     else:
    #         return [static(f"filestore/{x}") for x in self.image_hover.split(",")]

    # def get_image_hi_res_urls(self):
    #     if self.image_hi_res == "" or self.image_hi_res == None:
    #         return self.get_img_urls()
    #
    #     if settings.CONFIG_ENV == "dev":
    #         if os.getenv("IMG_URL"):  ## put in IMG_URL for live site to see all the imgs in dev
    #             return [
    #                 f"{os.getenv('IMG_URL')}/filestore/{x.strip()}"
    #                 for x in self.image_hi_res.split(",")
    #             ]
    #         else:
    #             return [static(f"/img/product/{x.strip()}") for x in self.image_hi_res.split(",")]
    #     else:
    #         return [static(f"filestore/{x}") for x in self.image_hi_res.split(",")]

    def get_image_hi_res_urls(self):
        if len(self.get_img_urls(image_type="image")):
            return self.get_img_urls(image_type="image")
        else:
            return [Product.PLACEHOLDER_IMG]

    def get_img_urls(self, image_type="thumb"):
        image_urls = []
        images_product = GalleryProduct.objects.filter(product=self)
        for image_product in images_product:
            image = image_product.image
            img_url = image.url if image else Product.PLACEHOLDER_IMG
            if image_type == "gallery":
                data_image_url = [
                    {
                        "image": img_url,
                        "thumb": image_product.image_thumbnail.url
                        if image_product.image_thumbnail
                        else img_url,
                        "hide_thumbnail": image_product.hide_thumbnail,
                        "sku_matching": image_product.sku_matching,
                    }
                ]
            elif image_type == "image":
                data_image_url = [image_product.image.url if image else Product.PLACEHOLDER_IMG]
            else:
                data_image_url = [
                    image_product.image_thumbnail.url if image_product.image_thumbnail else img_url
                ]
            image_urls.extend(data_image_url)
        return image_urls

    def get_image_hover_urls(self):
        if self.image_hover == "" or self.image_hover == None:
            return self.get_img_urls()
        image_hover_urls = [self.image_hover.url]
        return image_hover_urls

    def get_all_skus(self):
        product_code = self.get_product_sku()
        skus = []
        product_options = {'SIZE': [product_code]} if product_code else {}
        option_ids = []
        for opt in self.get_product_options():
            if opt.productoption and opt.productoption.include_gallery:
                if opt.productoption.option_type not in product_options:
                    product_options[opt.productoption.option_type] = []
                option_ids.append(opt.productoption.id)
        option_queryset = Product.get_options(option_ids)
        if option_queryset:
            for obj in option_queryset.all():
                if obj.sku_addition:
                    if obj.sku_addition not in product_options[obj.productoption.option_type]:
                        product_options[obj.productoption.option_type].append(obj.sku_addition)
        skus = generate_combinations_recursive(list(product_options.values()))
        return skus

    def get_resources(self):
        items = {}
        product_resources_ids = []

        for opt in self.get_product_resources():
            opt_id = opt.productresource.id
            items[opt_id] = {
                "id": opt_id,
                "name": opt.productresource.name,
                "items": [],
            }
            product_resources_ids.append(opt_id)

        resources = Resource.objects.select_related("productresource").filter(
            productresource_id__in=product_resources_ids
        )
        for obj in resources:
            item = {
                "name": obj.name,
                "resource_url": obj.resource_url.url if obj.resource_url else "",
            }
            prod_resource_id = obj.productresource.id
            if items.get(prod_resource_id):
                items[prod_resource_id]["items"].append(item)
            else:
                items[prod_resource_id] = {
                    "id": prod_resource_id,
                    "name": obj.productresource.name,
                    "items": [item],
                }
        items = [value for value in items.values()]
        return items

    def get_video_urls(self):
        return [x.split("/")[-1] for x in self.video_url.split(",")]

    @cached_property
    def is_active(self):
        return self.active

    def get_price(self):
        return round(self.list_price, 2)
        ## below is legacy

        try:
            return round(self.price, 2)
        except Exception as e:
            user = get_current_user()

            # if user logged in, and part of a company
            if not (user and user.id and user.company_id and user.get_group_code() == "TRADE"):
                return self.retail_price  # annon user / retail user
            else:
                # logged in user assigned to a company
                # if they don't have a pricelist
                if user.company_id.pricelists.count == 0:
                    return self.list_price
                else:
                    # pricelist_item = (
                    #     PricelistItem.objects.filter(
                    #         product__sku=self.sku,
                    #         pricelist__uuid__in=user.company_id.pricelists,
                    #     )
                    #     .order_by("price")
                    #     .values_list("price", flat=True)[:1]
                    # )
                    # # if they're assigned a price for this prod
                    # if pricelist_item:
                    #     min_price = min(min(pricelist_item), self.list_price)
                    #     return min_price
                    # else:
                    #     return self.list_price
                    return self.list_price

    def get_max_price(self):
        max_price = self.list_price
        try:
            if self.total_price:
                max_price += self.total_price
        except:
            return 999
        return round(max_price, 2)

    def get_number_option(self):
        try:
            if self.number_total:
                number_total = self.number_total
            else:
                number_total = 0
        except:
            number_total = 0

        return number_total

    def get_price_html(self):
        price_html = "${:.2f}".format(round(float(self.get_price()), 2))
        if not self.check_can_purchase():
            price_html = "POA"
        # if self.get_max_price() < self.get_price():
        #     price_html += " - " + "$" + "{:.2f}".format(round(float(self.get_max_price()), 2))

        return price_html

    def get_categories(self):
        try:
            cat = self.category_ids.first()
            return cat.full_display()
        except Exception as exc:
            return ""

    def get_first_category_name(self):
        try:
            cat = self.category_ids.first()
            return cat.name
        except Exception as exc:
            return ""

    def get_three_levels_categories(self):
        full_display = self.get_categories()
        cat_name_term = full_display.split("/")

        if len(cat_name_term) >= 4:
            full_display = cat_name_term[3].rstrip()
        else:
            full_display = cat_name_term[-1]

        return full_display

    def get_product_sku(self):
        return self.code if self.code else ""

    def get_breadcrumbs(self, came_from_category=False, slug_category=None):
        cache_key = PRODUCT_BREADCRUMBS + str(self.sku)
        items = []
        items.append(
            {
                "name": self.name,
                "link": None,
            }
        )
        if came_from_category and slug_category:
            try:
                cat = Category.objects.get(slug=slug_category)
                cache_key += CATEGORY_BREADCRUMBS + str(cat.uuid)
            except Category.DoesNotExist:
                return self.get_default_breadcrumbs(items, cache_key)
            if cache_key in cache:
                return cache.get(cache_key)

            cat_breadcrumbs = cat.get_list_breadcrumbs(get_list=True)
            if cat_breadcrumbs:
                items.extend(cat_breadcrumbs)
                items = reversed(items)
                cache.set(cache_key, items)

        else:
            items = self.get_default_breadcrumbs(items, cache_key)
        return items

    def get_default_breadcrumbs(self, items, cache_key):
        if cache_key in cache:
            return cache.get(cache_key)
        cat = self.categories.first()
        if cat is not None:
            cache_key += CATEGORY_BREADCRUMBS + str(cat.uuid)
            if cache_key in cache:
                return cache.get(cache_key)
            else:
                while cat is not None:
                    slug = cat.get_absolute_url()
                    items.append(
                        {
                            "name": cat.name,
                            "link": reverse("category-grid", kwargs={"category_path": slug}),
                        }
                    )
                    cat = cat.parent_category
                items = reversed(items)
                cache.set(cache_key, items)
        return items

    def get_product_options(self):
        object_list = ProductOptionRel.objects.select_related(
            "product", "productoption", "default_option"
        ).filter(product__sku=self.sku)
        return object_list

    def get_product_resources(self):
        object_list = ProductResourceRel.objects.select_related(
            "product", "productresource"
        ).filter(product__sku=self.sku)
        return object_list

    def get_options(option_ids):
        object_list = Option.objects.select_related("productoption").filter(
            productoption__id__in=option_ids
        )
        return object_list

    def get_option_context(self):
        rectagle_options = {}
        radio_options = {}
        option_ids = []
        product_option_depend = []
        product_option_not_depend = []
        option_depend = []
        option_not_depend = []
        list_index = {
            "RECTANGLE": {},
            "RADIO": {},
            "option_depend": {},
        }
        index_rectagle = 0
        index_radio = 0

        default_sku = ""
        default_size_choice = "RECTANGLE"
        for opt in self.get_product_options():
            if opt.productoption.option_type == "SIZE":
                default_size_choice = opt.productoption.display_choice
            active = True
            opt_id = opt.productoption.id
            depends_on, not_depend_on = opt.productoption.get_depend_options()
            product_option_depend.extend(depends_on)
            product_option_not_depend.extend(not_depend_on)
            if depends_on:
                active = False

            option = {
                "uuid": opt_id,
                "type": opt.productoption.option_type,
                "name": opt.label if opt.label else opt.productoption.option_type,
                "cls": opt.productoption.get_cls(),
                "required": opt.required,
                "is_error": False,
                "default_option": {},
                "default_option_id": None,
                "options": [],
                "active": active,
            }
            if opt.default_option is not None:
                option["default_option_id"] = opt.default_option.id

            if opt.productoption.display_choice == "RADIO":
                radio_options[opt_id] = option
                list_index["RADIO"][opt_id] = index_radio
                index_radio += 1
            else:
                rectagle_options[opt_id] = option
                list_index["RECTANGLE"][opt_id] = index_rectagle
                index_rectagle += 1
            option_ids.append(opt_id)

        option_queryset = Product.get_options(option_ids)
        if option_queryset:
            for obj in option_queryset.all():
                active = True
                opt_id = obj.productoption.id
                depends_on, not_depend_on = obj.get_depend_options()
                option_depend.extend(depends_on)
                option_not_depend.extend(not_depend_on)
                if depends_on:
                    active = False
                item = {
                    "id": obj.id,
                    # "name": obj.label if obj.label else obj.name,
                    # "description": obj.description,
                    "name": obj.name,
                    "price": round(float(obj.price_adjust), 2),
                    "image_url": obj.get_image_url(),
                    "sku_addition": obj.sku_addition if obj.sku_addition else "",
                    "dimension": obj.get_dimension(),
                    "active": active,
                }
                if rectagle_options.get(opt_id):
                    rectagle_options[opt_id]["options"].append(item)
                    if item and rectagle_options[opt_id]["default_option_id"] and rectagle_options[opt_id]["default_option_id"] == obj.id:
                        rectagle_options[opt_id]["default_option"] = item
                if radio_options.get(opt_id):
                    radio_options[opt_id]["options"].append(item)
                    if item and radio_options[opt_id]["default_option_id"] and radio_options[opt_id]["default_option_id"] == obj.id:
                        radio_options[opt_id]["default_option"] = item

                if not list_index.get("option_depend").get(opt_id):
                    list_index["option_depend"][opt_id] = {
                        "pointer": 0,
                        "options": {obj.id: 0},
                    }
                else:
                    list_index["option_depend"][opt_id]["pointer"] += 1
                    list_index["option_depend"][opt_id]["options"].update(
                        {obj.id: list_index["option_depend"][opt_id]["pointer"]}
                    )

        no_depend = True if not product_option_depend and \
                            not product_option_not_depend and \
                            not option_depend and \
                            not option_not_depend else False

        return {
            "RECTANGLE": list(rectagle_options.values()),
            "RADIO": list(radio_options.values()),
            "product_option_depend": product_option_depend,
            "product_option_not_depend": product_option_not_depend,
            "option_depend": option_depend,
            "option_not_depend": option_not_depend,
            "no_depend": no_depend,
            "default_size_choice": default_size_choice,
            "list_index": list_index,
        }

    def get_gallery_context(self):
        i = 0
        image_urls = self.get_img_urls(image_type="gallery")
        gallery = []
        img_length = len(image_urls)
        if img_length:
            for i in range(img_length):
                try:
                    img_item = {"image": image_urls[i]["image"], "thumb": image_urls[i]["thumb"],
                                "hide_thumbnail": image_urls[i]["hide_thumbnail"], "sku_matching": image_urls[i]["sku_matching"]}
                except Exception as e:
                    img_item = {"image": image_urls[i]["image"], "thumb": image_urls[i]["thumb"]}

                gallery.append(img_item)
        return gallery

    def get_relate_items(self):
        products = Product.objects.filter(
            sku__in=RelateProduct.objects.select_related("product", "relate_product")
            .filter(product__sku=self.sku)
            .values("relate_product__sku")
        )
        items = []
        for obj in products:
            item = {
                "name": obj.name,
                "slug": obj.get_absolute_url(),
                "min_price": obj.get_price(),
                "max_price": obj.get_max_price(),
                "image_urls": obj.get_image_hi_res_urls(),
            }
            items.append(item)
        return items

    def get_dimension(self):
        if not self.dimension:
            return ""
        return self.dimension

    def check_can_purchase(self):
        if self.can_purchase and float(self.list_price) > 0:
            return True
        return False


### through model so we can sequence them correctly
class RelateProduct(models.Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = ["product", "relate_product"]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    relate_product = models.ForeignKey(
        Product, related_name="relate_item_all", on_delete=models.CASCADE, null=True
    )
    sequence = models.PositiveIntegerField(default=0)


class GroupProduct(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    products = models.ManyToManyField(Product, through="GroupProductRel")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(GroupProduct, self).save(*args, **kwargs)


class GroupProductRel(models.Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = ["product", "group_product"]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    group_product = models.ForeignKey(GroupProduct, on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField(default=0)


class GalleryProduct(models.Model):
    class Meta:
        ordering = ["sequence"]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    image = models.FileField(upload_to="images/products/", null=True, blank=True)
    image_thumbnail = models.FileField(
        upload_to="images/products/thumbnail/", null=True, blank=True
    )
    hide_thumbnail = models.BooleanField(default=False)
    sku_matching = models.CharField(max_length=255, null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)


class ProductOption(models.Model):
    class OPTION_TYPE(models.TextChoices):
        COLOUR = ("COLOUR", "Colour")
        SIZE = ("SIZE", "Size")
        SLAB_TOP = ("SLAB_TOP", "Slab Top")
        BASIN = ("BASIN", "Basin")
        EXTRUSION = ("EXTRUSION", "Extrusion")
        TAP_HOLE = ("TAP_HOLE", "Tap Hole")
        COSMETIC_DRAWER = ("COSMETIC_DRAWER", "Cosmetic Drawer")
        HANDLES = ("HANDLES", "Handles")
        DEMISTER = ("DEMISTER", "Demister")
        OTHER = ("OTHER", "Other")

    class DISPLAY_CHOICE(models.TextChoices):
        RECTANGLE = ("RECTANGLE", "Rectangle")
        RADIO = ("RADIO", "Radio")

    option_type = models.CharField(choices=OPTION_TYPE.choices, max_length=25)
    include_gallery = models.BooleanField(default=False)
    display_choice = models.CharField(
        choices=DISPLAY_CHOICE.choices, max_length=25, default=DISPLAY_CHOICE.RECTANGLE
    )
    option_name = models.CharField(
        help_text="friendly internal name to help identify the option set eg: VISTA COLOURS",
        max_length=250,
        null=True,
    )

    product_option_dependencies = models.ManyToManyField(
        "products.ProductOption", through="ProductOptionDependRel", related_name="depend_product_options_all"
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        str_name = (self.option_type + ": " + str(self.option_name) + " - " + str(self.product) if self.product else
                    self.option_type + ": " + str(self.option_name))
        return str_name

    def copy_options(self):
        option_list = []
        for option in self.option_set.all():
            option.pk = None
            option.save()
            option_list.append(option)
        return option_list

    def copy_depend_options(self):
        depend_option_list = []
        for depend_option in self.productoptiondependrel_set.all():
            depend_option.pk = None
            depend_option.save()
            depend_option_list.append(depend_option)
        return depend_option_list


    def get_depend_options(self):
        """
            type: (type_option_choice, self_id , depend_option_id)
        """
        product_option_dependencies = ProductOptionDependRel.objects.select_related(
            "productoption", "depend_productoption", "depend_option"
        ).filter(productoption=self)
        list_depend_options_available = []
        list_depend_options_unavailable = []
        for obj in product_option_dependencies:
            if obj.depend_option:
                if not obj.unavailable:
                    list_depend_options_available.append({obj.depend_option.id: {self.display_choice: self.id}})
                else:
                    list_depend_options_unavailable.append({obj.depend_option.id: {self.display_choice: self.id}})
        return list_depend_options_available, list_depend_options_unavailable


    # def save(self, *args, **kwargs):
    #     super(ProductOption, self).save(*args, **kwargs)
    #     if self.product is not None:
    #         exists_prod = ProductOptionRel.objects.select_related("product", "productoption").filter(
    #             product__sku=self.product.sku,
    #             productoption__id= self.id
    #         )
    #         if exists_prod.count() == 0:
    #             prod_opt_rels = {
    #                 "product": self.product,
    #                 "productoption": self
    #             }
    #             obj = ProductOptionRel(**prod_opt_rels)
    #             obj.save()

    def get_cls(self):
        return "form-field " + self.option_type.lower()


class Option(models.Model):
    class Meta:
        ordering = ["sequence"]

    productoption = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    # label = models.CharField(max_length=200, null=True, blank=True)
    sku_addition = models.CharField(max_length=100, null=True, blank=True)
    # description = models.CharField(max_length=200, null=True, blank=True)
    price_adjust = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    image = models.FileField(upload_to="images/products/option/", null=True, blank=True)
    image_url = models.CharField(max_length=1000, null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)
    dimension = models.CharField(max_length=100, null=True, blank=True)

    option_dependencies = models.ManyToManyField(
        "products.Option", through="OptionDependRel", related_name="depend_options_all"
    )

    def __str__(self):
        return self.productoption.__str__() + " - " + self.name

    def get_option_name(self):
        return self.get_name()

    def get_option_name_no_html(self):
        return self.get_name(keep_html=False)

    def get_name(self, keep_html=True):
        # name = self.label if self.label else self.name
        name = self.name
        if self.price_adjust > 0:
            name += " (+$" + "{:.2f}".format(round(float(self.price_adjust), 2)) + ")"
        if keep_html:
            return mark_safe(name)
        else:
            return strip_tags(name)

    def get_option_label(self):
        productOptionRel = (
            ProductOptionRel.objects.select_related("product", "productoption")
            .filter(
                # product__sku=self.product.sku,
                productoption__id=self.productoption.id,
            )
            .first()
        )
        labelOfOption = productOptionRel.label if productOptionRel else None
        label = labelOfOption if labelOfOption else self.productoption.option_type
        return label

    def get_image_url(self):
        if self.image:
            return self.image.url
        elif self.image_url:
            return f"{settings.MEDIA_URL}images/products/option/{self.image_url}"
        return ""

    def get_dimension(self):
        if not self.dimension:
            return ""
        return self.dimension

    def get_depend_options(self):
        """
            type: {depend_option_id: self_id}
        """
        option_dependencies = OptionDependRel.objects.select_related(
            "option", "depend_productoption", "depend_option"
        ).filter(option=self)
        list_depend_options_available = []
        list_depend_options_unavailable = []
        for obj in option_dependencies:
            if obj.depend_option:
                if not obj.unavailable:
                    list_depend_options_available.append({obj.depend_option.id: {self.productoption.display_choice: {self.productoption.id: self.id}}})
                else:
                    list_depend_options_unavailable.append({obj.depend_option.id: {self.productoption.display_choice: {self.productoption.id: self.id}}})
        return list_depend_options_available, list_depend_options_unavailable




class ProductOptionDependRel(models.Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = ["productoption", "depend_productoption", "depend_option"]

    productoption = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    depend_productoption = models.ForeignKey(ProductOption, on_delete=models.CASCADE, related_name="depend_productoption_all")
    sequence = models.PositiveIntegerField(default=0)
    depend_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    unavailable = models.BooleanField(default=False)

    def __str__(self):
        return self.productoption.__str__() + " - Depend on: " + self.depend_productoption.__str__()


class OptionDependRel(models.Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = ["option", "depend_option", "depend_productoption"]

    option = models.ForeignKey(Option, on_delete=models.CASCADE)
    depend_productoption = models.ForeignKey(ProductOption, on_delete=models.CASCADE,
                                             related_name="depend_productoption_option")
    depend_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True,
                                      related_name="depend_option")
    sequence = models.PositiveIntegerField(default=0)
    unavailable = models.BooleanField(default=False)

    def __str__(self):
        return self.option.__str__() + " - Depend on: " + self.depend_option.__str__()

### through model so we can sequence them correctly
class ProductOptionRel(models.Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = ["product", "productoption"]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    productoption = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    label = models.CharField(max_length=200, null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    default_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.product.sku + " - " + self.productoption.__str__()


class ProductResource(models.Model):
    class Meta:
        ordering = ["sequence"]

    name = models.CharField(max_length=200)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    sequence = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        super(ProductResource, self).save(*args, **kwargs)
        if self.product is not None:
            exists_prod = ProductResourceRel.objects.select_related(
                "product", "productresource"
            ).filter(product__sku=self.product.sku, productresource__id=self.id)
            if exists_prod.count() == 0:
                prod_res_rels = {"product": self.product, "productresource": self}
                obj = ProductResourceRel(**prod_res_rels)
                obj.save()

    def __str__(self):
        if self.product:
            return self.product.name + " - " + self.name
        else:
            return self.name


class ProductResourceRel(models.Model):
    class Meta:
        ordering = ["sequence"]
        unique_together = ["product", "productresource"]

    productresource = models.ForeignKey(ProductResource, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    sequence = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.product.sku + " - " + self.productresource.__str__()


class Resource(models.Model):
    class Meta:
        ordering = ["sequence"]

    productresource = models.ForeignKey(ProductResource, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    resource_url = models.FileField(upload_to="assets/product_resource/", null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)


#####PRODUCTSERIALIZER
class ProductSerializer(serializers.ModelSerializer):
    get_absolute_url = serializers.CharField(read_only=True)
    get_img_urls = serializers.SerializerMethodField()  # calls get_get_imgs_ursl below
    price = serializers.SerializerMethodField()
    max_price = serializers.SerializerMethodField()
    number_total = serializers.SerializerMethodField()
    prod_can_purchase = serializers.SerializerMethodField()
    is_exact = serializers.SerializerMethodField()

    def __init__(self, instance=None, data=empty, search_term=None, **kwargs):
        self.search_term = search_term
        super().__init__(
            instance=instance,
            data=data,
            **kwargs
        )

    class Meta:
        model = Product
        fields = (
            "name",
            "code",
            "price",
            "image_hover",
            "active",
            "slug",
            "get_absolute_url",
            "get_img_urls",
            "max_price",
            "number_total",
            "prod_can_purchase",
            "is_exact"
        )

    def get_get_img_urls(self, prod):
        if len(prod.get_img_urls()):
            return prod.get_img_urls()
        else:
            return [Product.PLACEHOLDER_IMG]

    def get_price(self, prod):
        return prod.get_price()

    def get_max_price(self, prod):
        return prod.get_max_price()

    def get_number_total(self, prod):
        return prod.get_number_option()

    def get_prod_can_purchase(self, prod):
        return prod.check_can_purchase()

    def get_is_exact(self, prod):
        search_term = self.search_term
        context = search_term.split()
        sku_additions = prod.get_sku_additions
        is_exact = False
        if str(prod.sku).lower() == search_term.lower():
            is_exact = True
        else:
            try:
                new_sku_additions = set(context) - set(sku_additions)
                if len(new_sku_additions) == 0:
                    is_exact = True
            except Exception as e:
                pass
        return is_exact


class CategorySerializer(serializers.ModelSerializer):
    get_absolute_url = serializers.CharField(read_only=True)
    get_img_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("uuid", "name", "slug", "get_img_url", "get_absolute_url", "image_hover")

    def get_get_img_url(self, obj):
        return obj.get_img_url()
