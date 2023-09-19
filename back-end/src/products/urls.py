from django.urls import path, re_path
from django.views.decorators.cache import cache_page
from products import search, views, views_cart, views_category

urlpatterns = [
    # path("<slug:slug>", views.product_details, name="product-detail"),
    #TODO: remove this when have data=
    re_path(
        r"^categories/(?P<category_path>.*)/$",
        views_category.product_category,
        name="category-grid",
    ),
    path("api/cart/", views_cart.CartDetail.as_view()),
    path("api/cart-items/", views_cart.CartItemList.as_view(), name="api-cart-items"),
    path("api/cart-items/<str:uuid>", views_cart.CartItemList.as_view()),
    path("api/cart-coupon/", views_cart.CartCouponView.as_view()),
    path("api/products/search", search.product_search, name="product-search"),
    path(
        "product/search/",
        views_category.product_category,
        name="product-search-page",
    ),
    re_path(r'^laundry/?$', views_category.page_laundry, name="page-laundry"),
    path("product/cart/", views_cart.cart_view, name="cart"),
    path(
        "product/checkout/complete/<str:order_id>",
        views.complete,
        name="checkout-complete",
    ),
    path("product/checkout/", views.checkout, name="checkout"),
    path(
        "create_shipping_address/",
        views.create_shipping_address,
        name="create_shipping_address",
    ),
    path(
        "create_billing_address/",
        views.create_billing_address,
        name="create_billing_address",
    ),
    path("cart/coupon", views_cart.cart_coupon_post, name="cart_coupon"),
    path("cart/items-update", views_cart.cart_items_post, name="cart_items"),
    path("api/favourites-groups", views.favourite_groups),
    path(
        "api/reorder",
        views.api_reorder,
        name="api_reorder",
    ),
    path(
        "api/product/reload",
        views_category.product_category_reload,
        name="api_product_reload",
    ),
    re_path(r'^store-locations/?$', views.store_location, name="store_locations"),
    re_path(r'^(?P<slug>[\w-]+)/?$', views.product_details, name="product-detail"),
]
