import datetime
import os
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Product
from .models_cart import CartCoupon, CartItem
from .models_store_location import StoreLocation
from .utils import get_presigned_url, smtp_send

list_store_address_fields = [
    "name",
    "street",
    "suburb",
    "district",
    "phone_number",
]


###### ORDERITEM
class OrderItem(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    product_price = models.FloatField()
    product_quantity = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    product_sku = models.CharField(max_length=100, null=True)
    order_uuid = models.CharField(max_length=36)
    sequence = models.PositiveIntegerField()
    cart_item = models.ForeignKey(
        CartItem, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True
    )
    long_description = models.TextField(blank=True, null=True)

    @property
    def items(self):
        return self.cart_item.items

    def __str__(self):
        return f"Order Item {self.get_product_sku()}  - {self.product_quantity}"

    def get_subtotal(self):
        return float(self.product_quantity * self.product_price)

    def get_product_sku(self):
        return self.product.get_product_sku()

    def get_product_name(self):
        return self.product.name

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(OrderItem, self).save(*args, **kwargs)

    class Meta:
        ordering = ["sequence"]


####ORDER
class Order(models.Model):
    class PaymentMethods(models.TextChoices):
        c_d_card = ("c_d_card", "Credit Card")
        d_d = ("d_d", "Direct Debit")
        credit = ("credit", "Credit Account")

    uuid = models.CharField(primary_key=True, max_length=36)
    number = models.PositiveIntegerField(unique=True, null=True, blank=True)
    create_date = models.DateTimeField()

    order_notes = models.TextField(max_length=255, blank=True, null=True)
    payment_type = models.CharField(max_length=10, choices=PaymentMethods.choices)
    items = models.ManyToManyField(OrderItem, related_name="order")

    shipping_cost = models.FloatField()
    admin_fee = models.FloatField()
    subtotal = models.FloatField()
    order_tax = models.FloatField()
    order_total = models.FloatField()
    order_surcharge = models.FloatField()
    customer = models.ForeignKey(
        "customers.CustomUser", on_delete=models.SET_NULL, null=True, blank=True
    )
    company_id = models.ForeignKey(
        "customers.Company", on_delete=models.SET_NULL, null=True, blank=True
    )
    purchase_order_ref = models.CharField(max_length=254, blank=True, null=True)

    address_shipping = models.ForeignKey(
        "customers.Addresses",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="orders_shipping",
    )
    address_billing = models.ForeignKey(
        "customers.Addresses",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="orders_billing",
    )

    address_shipping_str = models.CharField(max_length=350, blank=True, null=True)
    address_billing_str = models.CharField(max_length=350, blank=True, null=True)
    odoo_is_imported = models.BooleanField(default=False)
    coupon = models.ForeignKey(CartCoupon, blank=True, null=True, on_delete=models.RESTRICT)
    coupon_value = models.FloatField(default=0)

    customer_name = models.CharField(max_length=254, blank=True, null=True)
    customer_email = models.CharField(max_length=254, blank=True, null=True)
    customer_phone = models.CharField(max_length=254, blank=True, null=True)
    store_location = models.ForeignKey(
        StoreLocation, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"Order to {self.customer_name} - {self.get_pleasant_id()}"  # on {self.create_date.strftime('%d/%m/%Y')}"

    def get_pleasant_id(self):
        if not self.create_date:
            year = datetime.datetime.now().strftime("%y")
        else:
            year = self.create_date.strftime("%y")
        return f"WO-{str(year)}{self.number}"

    @staticmethod
    def get_next_order_number():
        key = "ORDER_LAST_SEQUENCE"

        if not cache.get(key):
            last_ord = Order.objects.order_by("-number").first()
            if not last_ord:
                number = 1000
            else:
                number = last_ord.number + 1
            cache.set(key, number, timeout=None)
            return number
        else:
            return cache.incr(key)

    def get_subtotal(self):
        return float(sum([x.product_quantity * x.product_price for x in self.items]))

    def get_products(self):
        order_items = self.items.all()
        products = []
        for item in order_items:
            products.append(item.product)
        return products

    def get_absolute_url(self):
        return f"/customers/order_view/{self.uuid}"

    def save(self, *args, **kwargs):
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())

        if not self.create_date:
            self.create_date = timezone.now()

        super(Order, self).save(*args, **kwargs)

    def get_confirmation_date(self):
        if not self.confirmation_date:
            return "N/A"
        return self.confirmation_date.strftime("%d/%m/%Y")

    def get_delivery_partner_address(self):
        address = []
        if self.store_location:
            for field in list_store_address_fields:
                data = getattr(self.store_location, field)
                if field == "phone_number" and data:
                    address.append(f"P: {data}")
                    continue
                if data:
                    address.append(data)
        return address

    def send_email_confirmation(self):
        recipient = []
        email = [self.customer_email]  # must be a list
        EMAIL_CC = settings.EMAIL_CC
        customer_emails_of_store = self.store_location.get_customer_emails()

        subject = "Newtech order - " + self.get_pleasant_id()
        customer = {
            "full_name": self.customer_name,
            "email": self.customer_email,
            "phone": self.customer_phone,
        }
        store_location = self.store_location
        # remove first / from url
        if store_location.logo:
            logo_url = store_location.logo.url[1:]
            image_right = {
                "url": logo_url,
                "name": store_location.name,
            }

        billing_address = self.address_billing_str.split(",") if self.address_billing_str else []
        partner_address = self.get_delivery_partner_address()

        recipient.extend(email)
        recipient.append(EMAIL_CC)
        recipient.extend(customer_emails_of_store)

        html_content = render_to_string(
            "mail_order_confirm.html",
            {
                "order_obj": self,
                "payment_type": self.payment_type,
                "cart_items": self.items.all(),
                "user_email": customer["email"],
                "user_obj": customer,
                "BASE_URL": settings.BASE_URL,
                "STATIC_URL": settings.STATIC_URL,
                "BANK_ACCOUNT": settings.BANK_ACCOUNT,
                "store_location": store_location,
                "billing_address": billing_address,
                "partner_address": partner_address,
                "image_right": image_right if store_location.logo else None,
            },
        )

        plain_message = strip_tags(html_content)
        smtp_send(
            subject=subject,
            emails=recipient,
            body=plain_message,
            html_body=html_content,
        )

    @classmethod
    def get_available_payment_methods(self, request):
        return [x.value for x in Order.PaymentMethods if x.value in ("c_d_card", "d_d")]

    class Meta:
        ordering = ["-create_date"]


class OrderInvoice(models.Model):
    class PaymentStatus(models.TextChoices):
        PAID = ("PAID", "Paid")
        OPEN = ("OPEN", "Open")
        OVERDUE = ("OVERDUE", "Overdue")

    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=36)
    customer_id = models.ForeignKey(
        "customers.CustomUser", on_delete=models.RESTRICT, null=True, blank=True
    )
    company_id = models.ForeignKey(
        "customers.Company", on_delete=models.RESTRICT, null=True, blank=True
    )
    odoo_id = models.IntegerField(unique=True)
    total_exc_gst = models.FloatField()
    total_inc_gst = models.FloatField()
    date_invoice = models.DateTimeField(null=True)
    due_date = models.DateTimeField(null=True)
    invoice_source = models.CharField(max_length=100, null=True, blank=True)
    customer_po = models.CharField(max_length=254, default="")
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices)
    pdf_url = models.CharField(max_length=256, null=True, blank=True, default="")

    def get_source(self):
        return self.name + " - " + self.invoice_source

    def generate_pdf_presigned_url(self):
        """Generates a presigned url for cloudfront. Used to ensure that
        customers cannot view the invoices directly from cloudfront, and
        customers can't access other's invoices
        """
        url = settings.STATIC_URL + "private/" + self.pdf_url
        redirect = get_presigned_url(url)
        return redirect


class OrderInvoiceQuery(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)

    order_invoice_id = models.ForeignKey(
        "products.OrderInvoice", on_delete=models.RESTRICT, null=True, blank=True
    )
    query_type = models.CharField(max_length=256, null=True)
    query_message = models.TextField(null=True)

    customer_id = models.ForeignKey(
        "customers.CustomUser", on_delete=models.RESTRICT, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(OrderInvoiceQuery, self).save(*args, **kwargs)

    def send_email(self):
        EMAIL_CC = settings.DEFAULT_FROM_EMAIL
        subject = "Amtech Medical - Raise Invoice Query - " + self.order_invoice_id.get_source()
        recipient = [EMAIL_CC]

        html_content = render_to_string(
            "emails/mail_invoice_query.html",
            {
                "obj": self,
                "invoice_obj": self.order_invoice_id,
                "user_email": self.customer_id.email,
                "user_obj": self.customer_id,
                "BASE_URL": settings.BASE_URL,
                "STATIC_URL": settings.STATIC_URL,
            },
        )

        plain_message = strip_tags(html_content)
        smtp_send(
            subject=subject,
            emails=recipient,
            body=plain_message,
            html_body=html_content,
        )
