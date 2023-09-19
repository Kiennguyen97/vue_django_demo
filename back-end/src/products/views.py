import copy
import json
import os
import sys
import uuid

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.models import BlogPost
from customers.forms import *
from customers.models import *
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.db.models.expressions import Q
from django.forms.models import model_to_dict
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseNotFound,
    JsonResponse,
)
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse

from .forms import CartCouponForm, CheckoutForm, NewAddressForm
from .models import Category, Product
from .models_cart import CartCoupon, CartCouponInstance, CartItem, CustomerCart
from .models_order import Order, OrderInvoice, OrderItem
from .models_store_location import NZRegion, StoreLocation
from .serializers import CartItemSerializer, OrderItemSerializer, OrderSerializer, StoreLocationSerializer
from .tasks import get_nonce, send_email_confirmation, send_mail
from .views_cart import get_cart_summary_or_blank
from website.breadcrumbs import add_crumbs
from .utils import can_purchase_requried


sys.path.append("../")

ADDRESS_FIELDS = ['billing_name', 'billing_addr1', 'billing_addr2', 'billing_town', 'billing_postcode' ]



def product_details(request, slug):
    context = {}

    referer = request.META.get('HTTP_REFERER')
    if referer and '/categories/' in referer:
        came_from_category = True
        path_category = referer.split("/categories/")[1].split("/")
        slug_category = path_category[-1] if path_category[-1] else path_category[-2]
    else:
        came_from_category = False
        slug_category = None

    try:
        prod = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        raise Http404()

    if not prod.sku:
        raise Http404()

    add_crumbs(request, prod.get_breadcrumbs(came_from_category=came_from_category, slug_category=slug_category))
    options = prod.get_option_context()
    gallery = prod.get_gallery_context()
    relate_items = prod.get_relate_items()
    context["product"] = prod

    try:
        images = prod.get_img_urls(image_type='gallery')
        base_image_url = images[0]['image'] if images[0] and not images[0]['hide_thumbnail'] else images[1]['image']
    except:
        base_image_url = ''

    context["config"] = {
        "sku": prod.sku,
        "display_sku": prod.get_product_sku(),
        "can_purchase": prod.check_can_purchase(),
        "name": prod.name,
        "description_long": prod.description_long,
        "base_image": base_image_url,
        "gallery": gallery,
        "qty": 1,
        "price": round(float(prod.get_price()), 2),
        "options": options,
        "resources": prod.get_resources(),
        "relate_items": relate_items,
        "csrf_token":  get_token(request),
        "dimension": prod.get_dimension(),
        "number_total": prod.get_number_option(),
    }
    # if default_sku != "":
    #     context["config"]["display_sku"] = default_sku

    if request.method == "GET":
        context["PRODUCT_CANONICAL"] = request.build_absolute_uri(prod.get_absolute_url())
        return render(request, "product-details.html", context)

    elif request.method == "POST":
        pass


def favourite_groups(request):
    if request.user.is_authenticated:
        groups = FavouritesList.get_favourites_groups_sorted(request)
        group_list = [
            f"<option value=\"{group['uuid']}\">{group['display_name']}</option>"
            for group in groups
        ]
        return HttpResponse(
            ("".join(group_list)),
            status=200,
            content_type="text/html",
        )
    return HttpResponse(
        (""),
        status=200,
        content_type="text/html",
    )


def convert_address(d):
    add_str = ", ".join([d.get(field) for field in ADDRESS_FIELDS if d.get(field)])
    return add_str

@can_purchase_requried
def checkout(request):
    """
    item: cart_item
    """
    def get_longdesc(item):
        longdesc = "<div> <b class=\"sku-label\">Code:</b> <span class=\"sku\">{}</span> </div>"\
            .format(item.get_product_sku())
        if item.items:
            for item_option in item.items:
                longdesc += "<div> <b class=\"sku-label\">{}:</b> <span class=\"sku\">{}</span> </div>".\
                    format(item_option.option.get_option_label(), item_option.option.get_option_name_no_html())
        return longdesc

    ## pop the referrer out of the session so it doesnt stay around
    if request.session.get("referrer"):
        request.session["referrer"] = None

    ### check if there is cart items
    ci = request.session.get("cart_uuid")
    if ci:
        if request.method == "POST":
            form_data = json.loads(request.body.decode())

            form = CheckoutForm(form_data)
            if form.is_valid():
                respone = {}
                # get validated data from form
                your_details = form_data["your_details"]
                #  get first and last name from your_details['name'] if not have a space then last name is blank
                if " " in your_details["name"]:
                    first_name, last_name = your_details["name"].split(" ", 1)
                else:
                    first_name = your_details["name"]
                    last_name = ""

                nonce = form_data["payment_method_nonce"]
                uuid_merchant = form_data["address_merchant"]
                billing_address = convert_address(form_data["address-bill"])
                payment_type = form_data["payment-type"]
                assert payment_type in Order.get_available_payment_methods(request)

                cart = get_cart_summary_or_blank(request)

                order_obj = form.save(commit=False)
                order_obj.uuid = str(uuid.uuid4())
                order_obj.status = "order"
                order_obj.store_location = StoreLocation.objects.get(uuid=uuid_merchant)
                order_obj.address_shipping_str = billing_address
                order_obj.address_billing_str = billing_address
                order_obj.customer_name = your_details["name"]
                order_obj.customer_email = your_details["email"]
                order_obj.customer_phone = your_details["phone"]

                order_obj.shipping_cost = cart["total_shipping"]
                order_obj.admin_fee = cart["admin_fee"]
                order_obj.subtotal = cart["total_carts"]
                order_obj.order_tax = cart["total_gst"]
                order_obj.number = Order.get_next_order_number()
                if cart.get("cart_coupon"):
                    order_obj.coupon = cart["cart_coupon"].coupon_id
                    order_obj.coupon_value = cart["coupon_value"]

                if payment_type == "c_d_card":
                    surcharge_perc = settings.CREDIT_CARD_SURCHARGE[0]
                    surcharge_val = cart["total_total"] * surcharge_perc
                    order_obj.order_surcharge = surcharge_val
                    order_obj.order_total = cart["total_total"] * (1 + surcharge_perc)
                    order_obj.payment_type = "c_d_card"

                    data = {
                        'payment_method_nonce': nonce,
                        'first_name': first_name,
                        'last_name': last_name,
                        'your_details': your_details,
                        'order_obj': order_obj,
                    }

                    # create a transaction
                    try:
                        result = braintree_payment(data)
                    except Exception as e:
                        respone.update({
                            "status": "error",
                            "message": str(e),
                        })
                        return JsonResponse(respone)

                    # result = settings.BRAINTREE_GATEWAY.transaction.sale(
                    #     {
                    #         "amount": str(round(order_obj.order_total, 2)),
                    #         "order_id": order_obj.get_pleasant_id(),
                    #         "payment_method_nonce": nonce,
                    #         "options": {"submit_for_settlement": True},
                    #         "customer": {
                    #             "first_name": first_name,
                    #             "last_name": last_name,
                    #             "email": your_details["email"],
                    #         },
                    #     }
                    # )

                    if not result.is_success:
                        message = f"Processing Error: {result.message}"

                        respone.update({
                            "status": "error",
                            "message": message,
                            "customer_id": result.transaction.customer_details.id,
                        })

                        return JsonResponse(respone)

                elif payment_type == "d_d":
                    order_obj.order_surcharge = 0
                    order_obj.order_total = cart["total_total"]
                    order_obj.payment_type = "d_d"

                elif payment_type == "credit":
                    order_obj.order_surcharge = 0
                    order_obj.order_total = cart["total_total"]
                    order_obj.payment_type = "credit"

                order_obj.save()
                item_uuids = []

                # generate order lines
                for i, item in enumerate(cart["cart_items"]):
                    ord_item = OrderItem(
                        uuid=str(uuid.uuid4()),
                        product_sku=item.get_product_sku(),
                        product_price=item.get_price(),
                        product_quantity=item.product_quantity,
                        product=item.product,
                        order_uuid=order_obj.uuid,
                        cart_item=item,
                        sequence=i,
                        long_description=get_longdesc(item),
                    )
                    ord_item.save()
                    item_uuids.append(ord_item.uuid)
                    item.delete()

                order_obj.items.set(item_uuids)
                order_obj.save()

                CustomerCart.objects.filter(uuid=request.session["cart_uuid"]).delete()
                # CustomerCart.objects.filter(customer=request.user).delete()

                request.session["cart_uuid"] = ""
                # async send_email_confirmation
                send_email_confirmation(order_obj)

                respone = {
                    'uuid': order_obj.uuid,
                    'order_code': order_obj.get_pleasant_id(),
                    'status': 'success',
                    'message': 'Order created successfully'
                }

                return JsonResponse(respone)
            else:
                message = ", ".join([x[0] for _, x in form.errors.items()])
                context = {
                    'status': 'error',
                    'message': message
                }
                return JsonResponse(context)
        elif request.method == "GET":
            raise Http404()
    else:
        return redirect("cart")

def braintree_payment(data):
    nonce = data['payment_method_nonce']
    first_name = data['first_name']
    last_name = data['last_name']
    your_details = data['your_details']
    order_obj = data['order_obj']

    try:
        existing_customer = settings.BRAINTREE_GATEWAY.customer.find(your_details['customer_id'])
    except:
        existing_customer = None

    # data create transaction
    data_submit_sale = {
        "amount": str(round(order_obj.order_total, 2)),
        "order_id": order_obj.get_pleasant_id(),
        "options": {"submit_for_settlement": True},
        "customer_id": "",
    }

    if existing_customer:
        # If customer exists, use their customer ID to create a transaction
        data_submit_sale['customer_id'] = existing_customer.id
        result = settings.BRAINTREE_GATEWAY.transaction.sale(data_submit_sale)
    else:
        # If customer doesn't exist, create a new customer and use their customer ID to create a transaction
        customer_result = settings.BRAINTREE_GATEWAY.customer.create({
            "payment_method_nonce": nonce,
            "first_name": first_name,
            "last_name": last_name,
            "email": your_details['email']
        })
        data_submit_sale['customer_id'] = customer_result.customer.id
        result = settings.BRAINTREE_GATEWAY.transaction.sale(data_submit_sale)
    return result



def complete(request, order_id):
    user = request.user
    if not user:
        isFirstPurchase = "true"
    else:
        order_count = Order.objects.filter(~Q(uuid=order_id), customer_id=user.id).count()
        if order_count > 0:
            isFirstPurchase = "false"
        else:
            isFirstPurchase = "true"

    order = Order.objects.get(uuid=order_id)
    order_id = order.get_pleasant_id()
    order_items = order.items.all()
    items = []
    for item in order_items:
        categories = []
        product = item.product
        cat = product.category_ids.first()
        items.append(
            {
                "sku": product.sku,
                "name": product.name,
                "category": cat.full_display(),
                "price": item.product_price,
                "quantity": item.product_quantity,
            }
        )
    json_items = json.dumps(items)
    context = {
        "order": order,
        "user": user,
        "products": json_items,
        "is_first_purchase": isFirstPurchase,
    }
    return render(request, "complete.html", context=context)


class OrderItemList(APIView):
    def get_object(self, uuid):
        try:
            return OrderItem.objects.get(uuid=uuid)
        except OrderItem.DoesNotExist:
            raise Http404

    def post(self, request, format=None):
        serializer = OrderItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, uuid, format=None):
        order_item = self.get_object(uuid)
        serializer = OrderItemSerializer(order_item)
        return Response(serializer.data)

    def put(self, request, uuid, format=None):
        order_item = self.get_object(uuid)
        serializer = OrderItemSerializer(order_item, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uuid, format=None):
        order_item = self.get_object(uuid)
        order_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderList(APIView):
    def get(self, request, format=None):
        order = Order.objects.all()
        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "GET"])
@login_required(login_url="login")
def create_billing_address(request):
    return create_generic_address(request, "BILL")


@api_view(["POST", "GET"])
@login_required(login_url="login")
def create_shipping_address(request):
    return create_generic_address(request, "SHIP")


def create_generic_address(request, addr_type=None):
    assert type == None or addr_type in ["BILL", "SHIP"]
    if request.method == "POST":
        form = NewAddressForm(request.data)
        if form.is_valid():
            address_obj = form.save(commit=False)
            address_obj.type_address = addr_type

            if request.user.get_group_code() == "TRADE":
                address_obj.company_id = request.user.company_id
            else:
                address_obj.customer = request.user

            address_obj.save()
            return Response(
                {"address": model_to_dict(address_obj), "status": status.HTTP_201_CREATED}
            )

        else:
            msg_string = ""
            for _, y in form.errors.items():
                msg_string += y[0]
            # messages.error(request, msg_string)
            return Response({"status": "error", "message": msg_string})

    if request.method == "GET":
        form = NewAddressForm()
        context = {"form": form}
        return render(request, "checkout.html", context)


@login_required(login_url="login")
def api_reorder(request):
    order_id = request.POST.get("order_id")
    errors = []
    i = 0
    try:
        order = request.user.get_order(uuid=order_id)
        order_items = OrderItem.objects.select_related("product").filter(order_uuid=order_id)
        for order_item in order_items:

            if order_item.product.is_on_sale:
                product_price = order_item.product.get_discount_price()
            else:
                product_price = order_item.product.get_price()

            data = {
                "product_sku": order_item.product.sku,
                "product_quantity": order_item.product_quantity,
                "product_price": product_price,
            }
            serializer = CartItemSerializer(data=data)
            if serializer.is_valid():
                is_pass = serializer.update_or_save(request)
                if not is_pass:
                    msg_string = f"The {order_item.product.sku} product does not exist"
                    errors.append(msg_string)
                else:
                    i += 1
    except Exception as e:
        from customers.account.odoo_order_client import OrderClient

        orderClient = OrderClient()
        order_items = orderClient.get_skus(order_id=order_id)
        objs = Product.objects.filter(sku__in=order_items.keys())
        if objs.count():
            for obj in objs:
                product_quantity = order_items[obj.sku]
                data = {
                    "product_sku": obj.sku,
                    "product_quantity": product_quantity,
                    "product_price": obj.get_price(),
                }
                serializer = CartItemSerializer(data=data)
                if serializer.is_valid():
                    is_pass = serializer.update_or_save(request)
                    if not is_pass:
                        msg_string = f"The {order_item.product.sku} product does not exist"
                        errors.append(msg_string)
                    else:
                        i += 1

    if len(errors):
        msg = ",".join(errors)
        messages.error(request, msg)

    if i > 0:
        messages.success(
            request, f"The {i} item(s) in this order have been successfully added to cart"
        )

    message_html = loader.render_to_string("message.html", None, request, using=None)

    return HttpResponse((message_html), status=200, content_type="text/html")

@api_view(["POST", "GET"])
def store_location(request):
    if request.method == "POST":
        region_id = request.data.get("region_uuid")
        store_lists, resellers = StoreLocation.get_store_location_by_region_id(region_id=region_id)
        store_lists_serializer = StoreLocationSerializer(store_lists, many=True)
        resellers_serializer = StoreLocationSerializer(resellers, many=True)
        context = {
            "store_lists": store_lists_serializer.data,
            "resellers": resellers_serializer.data,
        }
        return Response(context)
    else:
        add_crumbs(request, [
            {
                "name": "Nationwide Stockists",
                "link": None
            }
        ])
        items = [
            {
                "uuid": "",
                "name": ""
            }
        ]
        object_list = NZRegion.get_all_items()
        if len(object_list):
            items = items + object_list
        
        config = {
            "items": items,
            "csrf_token":  get_token(request),
            "url_key": reverse("store_locations"),
        }

        return render(request, "store_location/store_location.html", context={"config": config})


