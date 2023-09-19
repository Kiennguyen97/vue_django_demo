import uuid

from crum import get_current_user

from django.conf import settings
from django.db import models
from django.db.models import Count, Q, Sum

from .models import Product


###CUSTOMERCART
class CustomerCart(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    customer = models.ForeignKey(
        "customers.CustomUser", on_delete=models.SET_NULL, null=True, blank=True
    )
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.uuid

    @property
    def items(self):
        return self.cart_items.all().prefetch_related("product")

    def generate_shipping_cost(self):
        """Use this func to gen shipping rate for an order"""
        cart_items = self.items

        subtotal = sum([x.product.get_price() * x.product_quantity for x in cart_items])
        # shipping_cost = (
        #     settings.SHIPPING_FLAT_RATE if subtotal < settings.FREE_SHIPPING_THRESHOLD else 0
        # )
        shipping_cost = 0
        return shipping_cost

    def generate_admin_fee(self):
        """Use this func to gen admin_fee cost"""
        # amf = settings.ADMIN_FEE_PRICE
        amf = 0
        user = get_current_user()
        if user and user.is_authenticated:
            if user.company_id:
                if user.company_id.no_admin_fee == True:
                    amf = 0

        return amf

    def get_breadcrumbs(self):
        items = [
            {
                "name": "Your Cart",
                "link": None,
            }
        ]
        return items


    def get_summary(self, blank=None) -> dict:
        """Gets summary for api view, checkout, cart, etc"""
        context = {
            "cart_obj": self,
            "cart_items": [],
            "total_carts": 0.00,
            "total_shipping": 0.00,
            "total_gst": 0.00,
            "total_total": 0.00,
            "coupon_value": 0.00,
            "admin_fee": 0.00,
        }
        total_carts = 0

        ## if blank, return empty, saves the db shizz.
        if blank:
            return context

        cart_items = CartItem.objects.filter(cart__uuid=self.uuid).prefetch_related("product")
        # only one coupon per cart, sozz
        coupon_instance = CartCouponInstance.objects.filter(cart_id=self.uuid).first()
        total_quantity = 0
        if len(cart_items) > 0:
            for item in cart_items:
                product_price = float(item.get_price())
                total_quantity += float(item.product_quantity)
                total_carts += product_price * float(item.product_quantity)

            if coupon_instance:
                coupon_value = coupon_instance.calculated_discount
            else:
                coupon_value = 0

            shipping_cost = self.generate_shipping_cost()
            admin_fee = self.generate_admin_fee()
            total_gst = (total_carts + shipping_cost + admin_fee - coupon_value) * settings.GST_RATE
            # total_total = total_carts + shipping_cost + admin_fee - coupon_value + total_gst
            total_total = total_carts + shipping_cost + admin_fee - coupon_value
            context["cart_items"] = cart_items
            context["cart_coupon"] = coupon_instance
            context["coupon_value"] = coupon_value
            context["total_carts"] = round(total_carts, 2)
            context["total_shipping"] = round(shipping_cost, 2)
            context["admin_fee"] = round(admin_fee, 2)
            context["total_gst"] = round(total_gst, 2)
            context["total_total"] = round(total_total, 2)
            context["total_quantity"] = int(total_quantity)
        return context

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(CustomerCart, self).save(*args, **kwargs)

    def can_purchase(self):
        can_purchase = True
        cart_items = self.items
        if len(cart_items) > 0:
            for item in cart_items:
                if not item.product.check_can_purchase():
                    can_purchase = False
                    break

        return can_purchase

### CARTITEM
class CartItem(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    product_sku = models.CharField(max_length=100)
    product_price = models.FloatField()  #### need to fix - this causes issues. shouldn't have

    # a price field, calculated until it's placed as an order
    product_quantity = models.PositiveIntegerField()
    create_date = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    cart = models.ForeignKey(CustomerCart, on_delete=models.CASCADE, related_name="cart_items")
    product_sku_option = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Cart Item {self.product_sku}  - {self.product_quantity}"

    @property
    def items(self):
        return self.cart_item_options.prefetch_related("productoption", "option", "cart_item").all()

    def check_item_options(self, cart_options=[]):
        _pass = False
        old_cart_options = self.items.values("productoption", "option")
        existing_cart_options = []
        new_cart_options = []
        for opt in old_cart_options:
            pk = f"{opt['productoption']}-{opt['option']}"
            existing_cart_options.append(pk)
        for o in cart_options:
            pk = f"{o['productoption_id']}-{o['option_id']}"
            new_cart_options.append(pk)
        last_opts = set(new_cart_options) - set(existing_cart_options)
        if len(last_opts) == 0:
            _pass = True
        return _pass

    def get_product_sku(self):
        # get options
        options = CartItemOption.objects.filter(cart_item=self)
        sku = self.product.get_product_sku()+" "
        if options:
            for option in options:
                sku_addition = option.option.sku_addition
                # print('****************')
                # print(option.option.productoption.option_type)
                # if option.option.productoption.option_type in ['EXTRUSION', 'TAP_HOLE']:
                #     sku += " "
                # if option.option.productoption.option_type in ['COSMETIC_DRAWER']:
                #     sku += "-"
                if option.option.productoption.option_type == 'SIZE':
                    sku = sku.replace(self.product.get_product_sku(), sku_addition)
                else:
                    sku += f"{sku_addition if sku_addition else ''} "
        return sku.strip()

    # TODO kiennv/TASK2646: add history for cart item
    def create_history(self, user, change=False, message=""):
        from django.contrib.admin.models import LogEntry, CHANGE, ADDITION
        from django.contrib.contenttypes.models import ContentType
        try:
            content_type = ContentType.objects.get_for_model(self)
            LogEntry.objects.create(
                content_type=content_type,
                object_id=self.pk,
                object_repr=str(self),
                action_flag=CHANGE if change else ADDITION,
                change_message=message,
                user=user  # Assuming you have access to the current user
            )
        except:
            pass

    def create_history_new(self, user):
        message = f"Created Cart Item {self.product_sku} - {self.product_quantity}"
        self.create_history(user=user, change=False, message=message)

    def create_history_change(self, user, message):
        change = True
        self.create_history(user=user, change=change, message=message)




    def get_count(request):
        count = 0
        ci = request.session.get("cart_uuid")
        if ci:
            count = CartItem.objects.filter(cart__uuid=ci).count()
        return count

    def get_item_price(self):
        # this makes sure to return 10.10 instead of 10.1 etc
        product_price = self.product.get_price()
        cart_item_options = self.items.values("cart_item__uuid").annotate(total_price=Sum("option__price_adjust")).distinct()
        total_price = 0
        for cart_item_option in cart_item_options:
            total_price += float(cart_item_option["total_price"])
        price = float(product_price) + total_price

        return round(float(price), 2)

    def get_price(self):
        price = self.get_item_price()

        return "{:.2f}".format(round(float(price), 2))

    def get_subtotal(self, base=False):
        # this makes sure to return 10.10 instead of 10.1 etc
        price = self.get_item_price()

        return "{:.2f}".format(round(float(self.product_quantity * price), 2))

    def get_base_subtotal(self):
        return self.get_subtotal(base=True)

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(CartItem, self).save(*args, **kwargs)

    def save_cart_option(self, *args, **kwargs):
        prod_opts = kwargs.get("cart_options")
        if prod_opts and len(prod_opts):
            for opt in prod_opts:
                opt["cart_item"] = self
                cart_item_opt_obj = CartItemOption(**opt)
                cart_item_opt_obj.save()

    def cannot_purchase(self):
        if not self.product.check_can_purchase():
            return True
        return False

    class Meta:
        ordering = ["create_date"]

### CARTITEM
class CartItemOption(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    productoption = models.ForeignKey("products.ProductOption", on_delete=models.CASCADE, null=True)
    option = models.ForeignKey("products.Option", on_delete=models.CASCADE, null=True)
    cart_item = models.ForeignKey(CartItem, on_delete=models.CASCADE, related_name="cart_item_options", null=True)

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(CartItemOption, self).save(*args, **kwargs)


class CartCoupon(models.Model):
    COUPON_TYPES = [
        ("PERCENT", "Total Percentage Discount"),
        ("FIXED", "Total Fixed Price Discount"),
        ("PRODUCT_PERC", "Product Specific Percentage Discount"),
        ("PRODUCT_PRICE", "Product Specific Price Discount"),
    ]
    coupon_code = models.CharField(max_length=15)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=COUPON_TYPES)

    def __str__(self):
        return f"Coupon [{self.coupon_code}] - {self.name} - {self.type}"


class CartCouponLine(models.Model):
    coupon_id = models.ForeignKey(
        CartCoupon, on_delete=models.RESTRICT, related_name="coupon_lines"
    )
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, blank=True, null=True)
    value = models.FloatField()

    def __str__(self):
        return f"{self.coupon_id.name} - {self.value}"


class CartCouponInstance(models.Model):
    coupon_id = models.ForeignKey(CartCoupon, on_delete=models.RESTRICT)
    cart_id = models.ForeignKey(CustomerCart, on_delete=models.CASCADE)
    coupon_code = models.CharField(max_length=15)

    @property
    def calculated_discount(self):
        if self.coupon_id.type == "PRODUCT_PRICE":
            ## only can apply one coupon line per product
            coupon_product = self.coupon_id.coupon_lines.first()
            the_product = self.cart_id.cart_items.filter(product=coupon_product.product)
            product_qty = the_product.aggregate(Sum("product_quantity"))

            if product_qty["product_quantity__sum"]:
                discount_total = coupon_product.value * product_qty["product_quantity__sum"]
                return round(discount_total, 2)
            else:
                return 0

        if self.coupon_id.type == "PRODUCT_PERC":
            discount_amount = 0
            for coupon_line in self.coupon_id.coupon_lines.all():
                relevant_cart_items = self.cart_id.cart_items.filter(product=coupon_line.product)
                cart_item_subtotal = sum(
                    [float(x.product.get_price()) * x.product_quantity for x in relevant_cart_items]
                )
                if cart_item_subtotal > 0:
                    discount_amount += coupon_line.value * cart_item_subtotal

            return round(discount_amount, 2)
