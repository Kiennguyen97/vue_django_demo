import uuid

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render
from django.template.loader import render_to_string

from .forms import CartCouponForm
from .models_cart import CartCoupon, CartCouponInstance, CartItem, CustomerCart
from .serializers import CartDetailSerializer, CartItemSerializer, StoreLocationSerializer
from website.breadcrumbs import add_crumbs
from .models_order import Order
from .models_store_location import NZRegion, StoreLocation
from django.urls import reverse
from django.middleware.csrf import get_token
from .tasks import get_nonce, send_email_confirmation, send_mail
from customers.models import CustomUser

def cart_items_post(request):
    cart_item_uuid = request.POST.get("id")
    uuid.UUID(cart_item_uuid)  ## assert
    if request.user and request.user.id:
        user = request.user
    else:
        user = CustomUser.objects.filter(is_superuser=True).first()

    if request.POST.get("action") == "update":
        try:
            cart_qty = int(request.POST.get("qtybutton"))
            obj = CartItem.objects.get(pk=cart_item_uuid)
            message = 'Quantity updated from {} to {}'.format(obj.product_quantity, cart_qty)
            obj.product_quantity = cart_qty
            if user:
                obj.create_history_change(user=user, message=message)
            obj.save()
        except:
            pass

    elif request.POST.get("action") == "delete":
        CartItem.objects.get(pk=cart_item_uuid).delete()

    ctx = get_cart_summary_or_blank(request)
    ctx["form"] = CartCouponForm()
    ctx["base_template"] = "cart/_partial.html"
    return render(request, "cart/cart-content-partial.html", context=ctx)


def cart_coupon_post(request):
    ### delete coupon instance
    if request.POST.get("action") == "delete":
        coupon_id = int(request.POST["id"])
        cart_id = CustomerCart.objects.filter(uuid=request.session.get("cart_uuid"))
        cart_coupons = CartCouponInstance.objects.filter(id=coupon_id, cart_id=cart_id.first())
        if cart_coupons:
            for cart_obj in cart_coupons:
                cart_obj.delete()

        ctx = get_cart_summary_or_blank(request)
        ctx["form"] = CartCouponForm()
        ctx["base_template"] = "cart/_partial.html"
        return render(request, "cart/cart-content-partial.html", context=ctx)

    ### adding coupon instance
    form = CartCouponForm(request.POST)
    if form.is_valid():
        coupon = form.cleaned_data["coupon_code"]
        new_coupon_item = CartCouponInstance(
            coupon_id=CartCoupon.objects.filter(coupon_code=coupon).first(),
            cart_id=CustomerCart.objects.get(uuid=request.session.get("cart_uuid")),
            coupon_code=coupon,
        )
        new_coupon_item.save()
        ctx = get_cart_summary_or_blank(request)
        ctx["base_template"] = "cart/_partial.html"
        return render(request, "cart/cart-content-partial.html", context=ctx)
    else:
        ## returning errors
        ctx = get_cart_summary_or_blank(request)
        ctx["form"] = form
        ctx["errors"] = [form.errors[x] for x, _ in dict(form.errors).items()]
        ctx["base_template"] = "cart/_partial.html"
        return render(request, "cart/cart-content-partial.html", context=ctx)


class CartCouponView(APIView):
    def delete(self, request):
        coupon_id = request.data["cartId"]
        cart_id = CustomerCart.objects.filter(uuid=request.session.get("cart_uuid"))
        cart = CartCouponInstance.objects.filter(id=int(coupon_id), cart_id=cart_id.first())
        if cart:
            for cart_obj in cart:
                cart_obj.delete()
        return Response({}, status=status.HTTP_200_OK)


def get_cart_summary_or_blank(request):
    cart_uuid = request.session.get("cart_uuid")
    ## if cart_uuid is in the session
    if cart_uuid:
        cart_instance = CustomerCart(uuid=cart_uuid)
        return cart_instance.get_summary()
    else:
        ## else, just return an empty cart. saves db call.
        cart_instance = CustomerCart()
        return cart_instance.get_summary()


class CartDetail(APIView):
    def get(self, request):
        data = get_cart_summary_or_blank(request)
        if data.get("cart_coupon"):
            coupon_name = data["cart_coupon"].coupon_id.name
        else:
            coupon_name = ""

        serializer = CartDetailSerializer(
            {
                "subtotal": data["total_carts"],
                "count": len(data["cart_items"]),
                "shipping": data["total_shipping"],
                "gst": data["total_gst"],
                "total": data["total_total"],
                "cart_coupon": coupon_name,
                "coupon_value": data["coupon_value"],
            }
        )
        return Response(serializer.data)


class CartItemList(APIView):
    def get_object(self, uuid):
        try:
            return CartItem.objects.get(uuid=uuid)
        except CartItem.DoesNotExist:
            raise Http404

    def get(self, request, format=None):
        ci = request.session.get("cart_uuid")
        if ci:
            cis = CartItem.objects.filter(cart__uuid=ci)
        else:
            cis = []
        serializer = CartItemSerializer(cis, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        items = request.data.get("items")
        if items and len(items):
            is_added = False
            for item in items:
                serializer = CartItemSerializer(data=item)
                if serializer.is_valid():
                    serializer.update_or_save(request)
                    is_added = True
            if is_added:
                # Remove message after add to cart success
                # data = {
                #     "message": "%s added to cart" % request.data.get("product_name"),
                # }
                return Response(data, status=status.HTTP_201_CREATED)
            else:
                return Response({}, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = CartItemSerializer(data=request.data)
            if serializer.is_valid():
                res = serializer.update_or_save(request)
                if res:
                    cart_res = CartItemSerializer(res)
                    data = {
                        "result": cart_res.data,
                        # Remove message after add to cart success
                        # "message": "%s added to cart" % cart_res.data["product_title"],
                    }
                    # time.sleep(0.5)
                    res_format = request.data.get("format")
                    if res_format and res_format == "html":
                        # Remove message after add to cart success
                        # messages.success(request, data["message"])
                        return render(request, "message.html", context={})
                    return Response(data, status=status.HTTP_201_CREATED)
                else:
                    return Response({}, status=status.HTTP_400_BAD_REQUEST)

        # invalid serializer
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, uuid, format=None):
        ci = self.get_object(uuid)
        serializer = CartItemSerializer(ci, data=request.data)
        if serializer.is_valid():
            res = serializer.update_cart_item(request, ci.product)
            return Response(res.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uuid, format=None):
        ci = self.get_object(uuid)
        ci.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def cart_view(request):
    if request.method == "POST":
        pass
    else:  # request.method == GET or other
        form = CartCouponForm()

        # re validate access rules on the products
        cart_uuid = request.session.get("cart_uuid")
        cart_instance = None

        if cart_uuid:
            cart_instance = CustomerCart(uuid=cart_uuid)
            add_crumbs(request, cart_instance.get_breadcrumbs())

        ctx = get_cart_summary_or_blank(request)
        ctx["form"] = form
        ctx["base_template"] = "cart/cart.html"
        ctx["BANK_ACCOUNT"] = settings.BANK_ACCOUNT

        # TODO: TASK2371
        if cart_instance and cart_instance.cart_items.count() > 0:
            available_payment_methods = Order.get_available_payment_methods(request)
            merchant_lists, region_lists = get_all_regions_available()
            ctx["config"] = {
                "client_token": get_nonce(),
                "csrf_token": get_token(request),
                "place_order_url": reverse("checkout"),
                "merchant_lists": merchant_lists,
                "region_lists": region_lists,
                "payment_methods": available_payment_methods,
                "is_get_view": True,
                "site_key": settings.RECAPTCHA_SITE_KEY,
            }

        return render(request, "cart/cart-content-partial.html", context=ctx)

def get_all_regions_available():
    uu = lambda: str(uuid.uuid4())
    region_exists = {}
    merchant_lists = {}
    region_lists = [{'code': 'all', 'label': 'All'}]
    store_lists, resellers = StoreLocation.get_all_store_location(can_appear_checkout=True)
    for store in store_lists:
        region = store.region
        store_list_serializer = StoreLocationSerializer(store)
        if region:
            if not region_exists.get(region.uuid):
                region_exists[region.uuid] = region
                region_lists.append({'code': region.uuid, 'label': region.name})
                merchant_lists[region.uuid] = {
                    "region": region.name,
                    "store_lists": [store_list_serializer.data],
                    "resellers": [],
                }
            else:
                merchant_lists[region.uuid]["store_lists"].append(store_list_serializer.data)
        else:
            merchant_lists[uu] = {
                "region": "",
                "store_lists": [],
                "resellers": [],
            }
            merchant_lists[uu]["store_lists"].append(store_list_serializer.data)

    # regions = NZRegion.objects.all()
    
    # for region in regions:
    #     store_lists, resellers = StoreLocation.get_store_location_by_region_id(region.uuid)
    #     store_lists_serializer = StoreLocationSerializer(store_lists, many=True)
    #     resellers_serializer = StoreLocationSerializer(resellers, many=True)
    #     if store_lists_serializer.data:
    #         merchant_lists[region.uuid] = {
    #             "region": region.name,
    #             "store_lists": store_lists_serializer.data,
    #             "resellers": resellers_serializer.data,
    #         }
    
    # region_lists += [{'code': key, 'label': value["region"]} for key, value in merchant_lists.items()]
    return merchant_lists, region_lists
