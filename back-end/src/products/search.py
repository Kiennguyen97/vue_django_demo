from crum import get_current_user
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.conf import settings
from django.db.models.expressions import OuterRef, Q, Subquery
from django.utils.text import slugify
from products.meili_search import client

from .models import (  # ProductTemplate,; ProductTemplateRel,; ProductTempSerializer,
    Category,
    Product,
    ProductSerializer,
)


def make_search(search_term, filters=[]):
    """Method for making searches.
    It will (should) make the search string safe (escape any special chars etc)
    Be sure to use this instead of building others throughout the app
    Returns a list of products
    """

    search_term = search_term.strip().lower()

    # try:
    #     product_queryset = Product.objects.filter(
    #         Q(name__ilike=search_term) | Q(sku__ilike=search_term) | Q(slug__ilike=search_term)
    #     )
    #     product_queryset.count()
    #
    # except Exception as e:
    #     product_queryset = Product.objects.filter(
    #         Q(name__icontains=search_term)
    #         | Q(sku__icontains=search_term)
    #         | Q(slug__icontains=search_term)
    #     )
    #
    # product_skus = [x for x in product_queryset.values_list('sku', flat=True)]
    # TODO: use melisearch
    product_skus = client.create_query(search_term)

    return product_skus


def make_search_dropdown(search_term, order="ordering"):
    """Method for making searches.
    It will (should) make the search string safe (escape any special chars etc)
    Be sure to use this instead of building others throughout the app
    Returns a list of products
    """

    search_term = search_term.strip().lower()

    try:
        product_skus = client.create_query(search_term)
        res = Product.objects.filter(Q(sku__in=product_skus, active=True))
        product_ordering = {key: i for i, key in enumerate(product_skus)}
        res = sorted(res, key=lambda x: product_ordering.get(x.sku, 999))
        return res

    except Exception as e:
        if settings.CONFIG_ENV == "prod":
            raise e

    try:
        product_queryset = Product.objects.filter(
            Q(name__ilike=search_term) | Q(code__ilike=search_term) | Q(slug__ilike=search_term)
        )
        product_queryset.count()

    except Exception as e:
        product_queryset = Product.objects.filter(
            Q(name__icontains=search_term)
            | Q(sku__icontains=search_term)
            | Q(slug__icontains=search_term)
        )
    return product_queryset.order_by(order)


@api_view(["GET"])
def product_search(request):
    search_term = request.query_params["product-search"].lower().strip()
    products = make_search_dropdown(search_term)
    try:
        total_count = products.count()
    except Exception as e:
        total_count = len(products)
    
    prods = products[:4]
    serializer = ProductSerializer(prods, many=True, search_term=search_term)
    context = {
        "total_count": total_count,
        "items": serializer.data
    }
    return Response(context)
