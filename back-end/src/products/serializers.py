import uuid

from rest_framework import serializers, status
from rest_framework.response import Response

from django.db import models
from django.db.models import fields
from django.http import Http404

from .models import Product
from .models_cart import CartItem, CustomerCart
from .models_order import Order, OrderItem
from .models_store_location import StoreLocation
from customers.models import CustomUser


class CartDetailSerializer(serializers.Serializer):
    subtotal = serializers.FloatField()
    count = serializers.IntegerField()
    shipping = serializers.FloatField()
    total = serializers.FloatField()
    gst = serializers.FloatField()
    cart_coupon = serializers.CharField(max_length=25)
    coupon_value = serializers.FloatField()


class CartItemSerializer(serializers.ModelSerializer):
    uuid = serializers.CharField(required=False)
    subtotal = serializers.SerializerMethodField("get_subtotal", required=False)
    product_img = serializers.SerializerMethodField("get_product_img", required=False)
    product_title = serializers.SerializerMethodField("get_product_title", required=False)
    product_slug = serializers.SerializerMethodField("get_product_slug", required=False)
    product_full_url = serializers.SerializerMethodField("get_product_url", required=False)
    # product = ProductSerializer()

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    def get_subtotal(self, obj):
        return obj.product.get_price() * obj.product_quantity

    def get_product_img(self, obj):
        if len(obj.product.get_img_urls()):
            return obj.product.get_img_urls()[0]
        return Product.PLACEHOLDER_IMG

    def get_product_title(self, obj):
        return obj.product.name

    def get_product_slug(self, obj):
        return obj.product.slug

    def get_product_url(self, obj):
        return obj.product.get_absolute_url()

    def update_cart_item(self, req, prod):
        prod_qty = self.validated_data["product_quantity"]

        self.save(product_quantity=prod_qty)
        return self

    def update_or_save(self, req):
        cart_options = req.data["cart_options"]
        cart_uuid = req.session.get("cart_uuid")
        product_sku_option = req.data["product_sku_option"]
        try:
            prod = Product.objects.get(sku=self.validated_data["product_sku"])
            # To check that the product can be purchased or not, (can use tools like postman or bots to purchase)
            if not prod.check_can_purchase():
                raise Exception(f"The {prod.sku} product cannot be purchased")
        except:
            return False

        prod_qty = self.validated_data["product_quantity"]

        if req.user and req.user.id:
            user = req.user
        else:
            # get superuser CustomUser
            user = CustomUser.objects.filter(is_superuser=True).first()

        if cart_uuid:
            try:
                ## if there is a cart for this customer
                existing_cart_obj = CustomerCart.objects.get(uuid=cart_uuid)
                if existing_cart_obj:

                    ## existing cart_items
                    existing_cart_item = CartItem.objects.filter(
                        product_sku__exact=prod.sku, cart__uuid=cart_uuid, product_sku_option__exact=product_sku_option
                    ).first()
                    ### cart items exist (this product)
                    if existing_cart_item:
                        # import pdb; pdb.set_trace()
                        is_pass = existing_cart_item.check_item_options(cart_options=cart_options)
                        if is_pass:
                            existing_qty = existing_cart_item.product_quantity
                            new_qty = existing_qty + prod_qty

                            existing_cart_item.product_quantity = new_qty
                            existing_cart_item.save()
                            message = 'Quantity updated from {} to {}'.format(existing_qty, new_qty)
                            if user:
                                existing_cart_item.create_history_change(user=user, message=message)
                            return existing_cart_item
                        else:
                            new_cart_item = self.save(
                                cart=existing_cart_obj,
                                product=prod,
                                product_quantity=prod_qty,
                            )
                            new_cart_item.save_cart_option(cart_options=cart_options)
                            if user:
                                new_cart_item.create_history_new(user=user)
                            return new_cart_item
                    else:
                        new_cart_item = self.save(
                            cart=existing_cart_obj,
                            product=prod,
                            product_quantity=prod_qty,
                        )
                        new_cart_item.save_cart_option(cart_options=cart_options)
                        if user:
                            new_cart_item.create_history_new(user=user)
                        return new_cart_item
            except:
                # else create new cart -
                # this occurs if there is a cart_uuid in session, but cart does not exist
                if req.user and req.user.id:
                    cart_obj = CustomerCart(customer=req.user)
                else:
                    cart_obj = CustomerCart()
                cart_obj.save()
                if cart_obj:
                    new_cart_item = self.save(cart=cart_obj, product=prod)
                    new_cart_item.save_cart_option(cart_options=cart_options)
                    if user:
                        new_cart_item.create_history_new(user=user)
                    req.session["cart_uuid"] = cart_obj.uuid
                    return new_cart_item
        else:
            if req.user and req.user.id:
                cart_obj = CustomerCart(customer=req.user)
            else:
                cart_obj = CustomerCart()
            cart_obj.save()

            if cart_obj:
                new_cart_item = self.save(cart=cart_obj, product=prod)
                new_cart_item.save_cart_option(cart_options=cart_options)
                if user:
                    new_cart_item.create_history_new(user=user)
                req.session["cart_uuid"] = cart_obj.uuid
                return new_cart_item

    class Meta:
        model = CartItem
        fields = [
            "uuid",
            "product_sku",
            "product_quantity",
            "product_price",
            "subtotal",
            "create_date",
            "product_img",
            "product_title",
            "product_slug",
            "product_full_url",
            "product_sku_option",
            # , 'product'
        ]
        ordering = ["-create_date"]


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "email_address",
            "phone_number",
            "first_name",
            "last_name",
            "company_name",
            "company_address",
            "address_1",
            "address_2",
            "city",
            "address_state",
            "address_postal",
            "order_notes",
            "payment_type",
            # 'items'
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "product_price",
            "product_quantity",
            "product",
            "order_uuid",
            "sequence",
        ]
        ordering = ["sequence"]


class CartSerializer(serializers.ModelSerializer):
    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    class Meta:
        model = CustomerCart
        fields = ["uuid"]


#####StoreLocationSerializer
class StoreLocationSerializer(serializers.ModelSerializer):
    map_view = serializers.SerializerMethodField()

    class Meta:
        model = StoreLocation
        fields = (
            "uuid",
            "name",
            "street",
            "suburb",
            "district",
            "zip_code",
            "phone_number",
            "logo",
            "thank_link",
            "map_view",
        )

    def get_map_view(self, obj):
        default_country = "New Zealand"
        query = f"{obj.name},{obj.street}"
        if obj.suburb:
            query += f",{obj.suburb}"
        query += f",{obj.district},{default_country}"
        return f"https://www.google.com/maps/search/?api=1&query={query}"
