import datetime
from botocore.signers import CloudFrontSigner

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from dateutil.relativedelta import relativedelta
from django.conf import settings
from functools import wraps
from django.http import JsonResponse

from .catalog import inject_cls
from .smtp import *


def move_guest_to_customer_cart(request, user):
    from products.models_cart import CartItem, CustomerCart

    cart_session_uuid = request.session.get("cart_uuid")
    cart_obj = CustomerCart.objects.filter(customer__id=user.id).first()
    if cart_obj:
        if cart_session_uuid:
            cart_items_queryset = CartItem.objects.filter(cart__uuid=cart_obj.uuid)
            if cart_items_queryset.count():
                guest_cart_items = CartItem.objects.filter(cart__uuid=cart_session_uuid).all()
                items = {}
                for cart_item in cart_items_queryset.all():
                    items[cart_item.product_sku] = cart_item

                for guest_cart_item in guest_cart_items:
                    if not items.get(guest_cart_item.product_sku):
                        setattr(guest_cart_item, "cart", cart_obj)
                        guest_cart_item.save()
                    else:
                        cart_item = items[guest_cart_item.product_sku]
                        qty = cart_item.product_quantity + guest_cart_item.product_quantity
                        setattr(cart_item, "product_quantity", qty)
                        cart_item.save()
                        guest_cart_item.delete()
            else:
                guest_cart_items = CartItem.objects.filter(cart__uuid=cart_session_uuid).all()
                for cart_item in guest_cart_items:
                    setattr(cart_item, "cart", cart_obj)
                    cart_item.save()
            CustomerCart.objects.filter(uuid=cart_session_uuid).delete()

        request.session["cart_uuid"] = cart_obj.uuid
    else:
        if cart_session_uuid:
            guest_cart_obj = CustomerCart.objects.filter(uuid=cart_session_uuid).first()
            setattr(guest_cart_obj, "customer", user)
            guest_cart_obj.save()


# def check_closed_purchase_by_user_and_product(args):
#     from products.models_lists import ClosedPurchaseGroupItem, ClosedPurchaseGroupRel
#
#     user = args.get("user")
#     product = args.get("product")
#     return (
#         ClosedPurchaseGroupItem.objects.select_related("product")
#         .select_related("closed_purchase_group")
#         .filter(
#             product__sku=product,
#             closed_purchase_group__uuid__in=ClosedPurchaseGroupRel.objects.select_related("company")
#             .select_related("closed_purchase_group")
#             .filter(company__uuid=user.company_id.uuid)
#             .values("closed_purchase_group__uuid"),
#         )
#         .count()
#     )


#### utils to generate cloudfront signed url
def rsa_signer(message):
    with open(settings.CLOUDFRONT_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(), password=None, backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())


def get_presigned_url(url):
    key_id = settings.CLOUDFRONT_KEY_ID
    expire_date = datetime.datetime.now() + relativedelta(days=2)
    cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)
    # Create a signed url that will be valid until the specfic expiry date
    # provided using a canned policy.
    signed_url = cloudfront_signer.generate_presigned_url(url, date_less_than=expire_date)
    return signed_url


def can_purchase(request):
    from products.models_cart import CartItem, CustomerCart
    can_purchase = False
    cart_uuid = request.session.get("cart_uuid")
    ## if cart_uuid is in the session
    if cart_uuid:
        cart_obj = CustomerCart.objects.filter(uuid=cart_uuid).first()
        if cart_obj is not None:
            can_purchase = cart_obj.can_purchase()
    return can_purchase

def can_purchase_requried(view_func):
    @wraps(view_func)
    def decorator(request, *args, **kwargs):
        required_can_purchase = can_purchase(request)
        if required_can_purchase:
            return view_func(request, *args, **kwargs)

        context = {
            "status": "error",
            "message": "There are products that cannot be purchased",
        }
        return JsonResponse(context)
    return decorator

