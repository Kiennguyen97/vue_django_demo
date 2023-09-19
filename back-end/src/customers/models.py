import binascii
import os
import uuid
from datetime import datetime
from email.policy import default
from secrets import choice
from typing import Any, Literal, Tuple

from customers.utils import send_invitation_email
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db import models
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Concat
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
# from products.models_lists import ClosedPurchaseGroupItem
from products.models_order import Order, OrderInvoice, OrderItem
from products.tasks import get_queue

# from products.utils import smtp_send
from .utils import InvitationStatus, Role, sync_address_to_odoo

# from pysodium import (
#     crypto_pwhash,
#     crypto_pwhash_MEMLIMIT_INTERACTIVE,
#     crypto_pwhash_OPSLIMIT_INTERACTIVE,
#     crypto_sign_SEEDBYTES,
# )


class CustomUserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class GroupExtend(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    group_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.group.name


class Company(models.Model):
    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)
    company_code = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=64, blank=True)
    no_admin_fee = models.BooleanField(default=False)
    sales_name = models.CharField(max_length=255, null=True)
    sales_email = models.CharField(max_length=64, null=True)

    @property
    def closed_purchase_groups(self):
        return self.closed_purchase_groups_all.all()

    def get_access_products(self):
        cpgs = self.closed_purchase_groups
        skus = []
        # skus = ClosedPurchaseGroupItem.objects.filter(closed_purchase_group__in=cpgs).values_list(
        #     "product", flat=True
        # )
        # return list(skus)
        return skus

    # @property
    # def pricelists(self):
    #     return self.pricelists_all.all()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(Company, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Company"


class CustomUser(AbstractUser):
    username = None
    # id = models.UUIDField(primary_key=True, default = str(uuid.uuid4()), editable=False)
    id = models.CharField(primary_key=True, max_length=36, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    group_id = models.ForeignKey(GroupExtend, on_delete=models.SET_NULL, null=True, blank=True)
    company_name = models.CharField(max_length=36, blank=True, null=True)
    password_hash = models.CharField(max_length=128, blank=True, null=True)
    odoo_id = models.IntegerField(blank=True, null=True)
    odoo_ref = models.CharField(max_length=64, blank=True, null=True)
    email_override = models.CharField(max_length=64, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    date_of_invitation = models.DateTimeField(null=True)
    invitation_status = models.CharField(
        max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.APPROVED
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    EMAIL_OVERRIDE_FIELD = "email_override"

    objects = CustomUserManager()

    # history_stored = models.BooleanField(default=False, help_text="Need to utilize this User for storing History action on Frontend of an Anonymous user with cart item.")


    def save(self, *args, **kwargs):
        # if blank, create new
        if self.id == "":
            self.id = str(uuid.uuid4())
        if self.group_id is None or self.group_id == "":
            self.group_id = GroupExtend.objects.filter(group_code="RETAIL").first()
        self.email = str(self.email).strip().lower()
        super(CustomUser, self).save(*args, **kwargs)

    @cached_property
    def is_trade(self):
        if self.group_id and self.group_id.group_code == "TRADE":
            return True
        return False

    def get_user_management(
        self,
        type_filter: Literal["total", "pending_invitations"],
        company_id: str,
        current_user_id: str = None,
        keyword: str = None,
        order_by: str = None,
        page: int = 0,
        page_size: int = 10,
    ):
        """Gets the list of users for user_management screen.
        Should only be called when the user is part of a company
        """

        customers = CustomUser.objects.filter(company_id=company_id).annotate(
            name=Concat(F("first_name"), Value(" "), F("last_name"), output_field=CharField())
        )
        # if current_user_id:
        #     customers = customers.filter()~Q(id=current_user_id))

        if type_filter == "total":
            customers = customers.filter(invitation_status=InvitationStatus.APPROVED)

        elif type_filter == "pending_invitations":
            customers = customers.filter(invitation_status=InvitationStatus.PENDING)

        if keyword:
            customers = customers.filter(name__contains=keyword)

        if not order_by:
            customers = customers.order_by("-date_joined")
        else:
            customers = customers.order_by(order_by)
        # Count
        count = customers.count()
        # Offset, Limt
        customers = customers[page * page_size : page_size]
        return customers, count

    def add_new_customer(
        self, first_name, last_name, email, role, company_id, admin_user
    ) -> Tuple[Any, None]:
        """Adds new customer to the company, called from the user management screen"""

        try:
            customer_query = CustomUser.objects.filter(email=email)
            if customer_query.exists():
                raise Exception(
                    "An account with this email already exists. Please contact the Amtech team for support - sales@amtech.co.nz"
                )

            # else, create new user...
            new_customer = CustomUser()
            new_customer.first_name = first_name
            new_customer.last_name = last_name
            new_customer.email = email
            new_customer.company_id = company_id
            new_customer.date_of_invitation = datetime.now()
            new_customer.invitation_status = InvitationStatus.PENDING
            new_customer.group_id = admin_user.group_id
            new_customer.role = role
            new_customer.save()

            company_name = company_id.name
            user_who_invited = admin_user

            # Send mail
            link_register = f"{settings.BASE_URL}{reverse('register')}?is_invitation=True&customer_id={new_customer.id}"
            context = {
                "BASE_URL": settings.BASE_URL,
                "company_name": company_name,
                "link_register": link_register,
                "user_who_invited": user_who_invited,
            }
            html_body = render_to_string("emails/confirm-invitation-email.html", context)

            send_invitation_email.delay(
                subject="Welcome to Amtech!",
                emails=[new_customer.email],
                body=strip_tags(html_body),
                html_body=html_body,
            )
            return new_customer
        except Exception as exc:
            raise Exception(str(exc))

    def get_group_code(self):
        """Gets group code or None"""
        if self.group_id:
            return self.group_id.group_code
        else:
            return None

    def get_company(self):
        """Gets company user is assigned or None"""
        if self.get_group_code() == "TRADE":
            return self.company_id
        else:
            return None

    @cached_property
    def has_closed_purchase_groups(self):
        """cached as may be called multiple times in a request"""
        if not self.company_id:
            return False
        else:
            return self.company_id.closed_purchase_groups.exists()

    @cached_property
    def get_access_products(self):
        """cached as may be called multiple times in a request"""
        if not self.company_id:
            return []
        else:
            return self.company_id.get_access_products()

    def get_email(self):
        if self.email_override:
            return self.email_override
        return self.email

    def get_addresses(self):
        address = ""
        if self.get_group_code() == "TRADE":
            address = Addresses.objects.filter(company_id__uuid=self.company_id.uuid)
        else:
            address = Addresses.objects.filter(customer__id=self.id)
        return address

    def get_billing_addresses(self):
        return self.get_addresses().filter(type_address="BILL")

    def get_shipping_addresses(self):
        return self.get_addresses().filter(type_address="SHIP")

    def get_orders(self, *args, **kwargs):
        if self.get_group_code() == "TRADE":
            order = Order.objects.filter(company_id__uuid=self.company_id.uuid)
        else:
            order = Order.objects.filter(customer__id=self.id)

        if kwargs.get("from"):
            date_from = kwargs.get("from")
            order = order.filter(create_date__gte=date_from)

        if kwargs.get("to"):
            date_to = kwargs.get("to")
            order = order.filter(create_date__lte=date_to)

        if kwargs.get("exclude_list"):
            order = order.filter(number__not_in=kwargs.get("exclude_list"))
        if kwargs.get("query"):
            query_string = kwargs.get("query")

            order = order.filter(
                Q(order_total__contains=query_string)
                | Q(number__contains=query_string)
                | Q(status__contains=query_string)
                | Q(create_date__contains=query_string)
            )

        return order

    def get_order_invoices(self, *args, **kwargs):
        if self.get_group_code() == "TRADE":
            invoices = OrderInvoice.objects.filter(company_id__uuid=self.company_id.uuid)
        else:
            invoices = OrderInvoice.objects.filter(customer_id=self.id)

        if kwargs.get("uuid"):
            assert uuid.UUID(kwargs.get("uuid"))
            invoices = invoices.filter(uuid=kwargs.get("uuid"))

        if kwargs.get("from"):
            date_from = kwargs.get("from")
            invoices = invoices.filter(date_invoice__gte=date_from)

        if kwargs.get("to"):
            date_to = kwargs.get("to")
            invoices = invoices.filter(date_invoice__lte=date_to)

        if kwargs.get("query"):
            query_string = kwargs.get("query")
            invoices = invoices.filter(
                Q(name__contains=query_string)
                | Q(total_exc_gst__contains=query_string)
                | Q(invoice_source__contains=query_string)
                | Q(customer_po__contains=query_string)
                | Q(payment_status__contains=query_string)
            )
        return invoices.order_by("-date_invoice")

    """
    def get_order_items(self, order_query):
        order_items = OrderItem.objects.filter(
            order_uuid__in=order_query.values("uuid")
        ).values("order_uuid").annotate(count=models.Count('uuid')).order_by('order_uuid').distinct()
        return order_items
    """

    def get_order(self, uuid):
        order = Order.objects.get(uuid=uuid)

        if self.get_group_code() == "TRADE":
            assert self.company_id.uuid == order.company_id.uuid
        else:
            assert self.id == order.customer_id

        return order

    def get_password_hash(self):
        # Get password hash

        return self.password_hash

    def is_password_hash(self):
        # Check password for User. It've created from Django or migration from Magento
        # if native django, then true
        # if from magento, then false
        return True if self.password else False

    def explode_password_hash(self):
        return self.get_password_hash().split(os.environ["PASSWORD_DELIMITER"])

    def validate_hash(self, password):
        # Compare password supplied by user
        # with hash password from Magento
        pw_hash = self.get_password_hash()
        explode_password_hash = self.explode_password_hash()
        salt = explode_password_hash[1]
        hash_version_latest = explode_password_hash[2]

        hash = crypto_pwhash(
            crypto_sign_SEEDBYTES,
            password,
            salt,
            crypto_pwhash_OPSLIMIT_INTERACTIVE,
            crypto_pwhash_MEMLIMIT_INTERACTIVE,
            int(hash_version_latest),
        )

        password_hash = "%s:%s:%s" % (
            binascii.hexlify(hash).decode("utf-8"),
            salt,
            hash_version_latest,
        )
        return password_hash == pw_hash

    def check_password(self, password):
        # Check password before login
        if self.is_password_hash():
            # default mage
            return super(CustomUser, self).check_password(password)
        else:
            if self.validate_hash(password):
                # check it from magento password
                # if correct, then set the password as
                # django password and delete old magento hash
                self.set_password(password)
                self.password_hash = None
                self.save()
                return True

        return None

    @staticmethod
    def check_reply_email(request):
        request_query_dict = request.POST
        email = request_query_dict.get("email")
        request_query_dict._mutable = True
        if email.find("@") == -1:
            email = email + settings.EMAIL_NO_REPLY
        request_query_dict.__setitem__("email", str(email).strip().lower())
        request_query_dict._mutable = False
        request.POST = request_query_dict

    @classmethod
    def get_email_override_field_name(cls):
        try:
            return cls.EMAIL_OVERRIDE_FIELD
        except AttributeError:
            return "email"


class Addresses(models.Model):
    class ALLOWED_ADDRESS(models.TextChoices):
        SHIP = ("SHIP", "Shipping ")
        BILL = ("BILL", "Billing")

    uuid = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=254)
    street_address_1 = models.CharField(max_length=254)
    street_address_2 = models.CharField(max_length=254, blank=True)
    city = models.CharField(max_length=64)
    phone = models.CharField(max_length=64, blank=True)
    company_id = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    type_address = models.CharField(max_length=15, choices=ALLOWED_ADDRESS.choices, default="SHIP")
    customer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    address_postal = models.CharField(verbose_name="Postal Code", max_length=32)
    odoo_id = models.IntegerField(default=0)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"/customers/update_address/{self.uuid}"

    def save(self, *args, **kwargs):
        # if blank, create new
        if self.uuid == "":
            self.uuid = str(uuid.uuid4())
        super(Addresses, self).save(*args, **kwargs)
        get_queue("default").enqueue(sync_address_to_odoo, self)

    def get_display_str_flat(self):
        addrs = [
            x
            for x in [
                self.street_address_1,
                self.street_address_2,
                self.city,
                self.phone,
                self.address_postal,
            ]
            if x != ""
        ]
        return ", ".join(addrs)

    def get_display_str_line_br(self):
        addrs = [
            x
            for x in [
                self.name,
                self.street_address_1,
                self.street_address_2,
                self.city,
                self.phone,
                self.address_postal,
            ]
            if x != ""
        ]
        return "\n".join(addrs)

    class Meta:
        verbose_name_plural = "Addresses"
