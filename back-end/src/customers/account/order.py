import math
import uuid
from datetime import datetime, timedelta

import pytz

from customers.account import BaseCustomerReload, CustomerReloadUps, Page
from customers.account.odoo_order_client import OrderClient
from customers.forms import Customerform
from customers.models import CustomUser
from customers.serializers import OrderItemOdooSerializer, OrderOdooSerializer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView


@method_decorator(login_required, name="dispatch")
class OrderHistory(UpdateView):
    model = CustomUser
    form_class = Customerform
    template_name = "account/order_history.html"

    def get_context_data(self, **kwargs):
        if self.object.id == self.request.user.id:
            context = super().get_context_data(**kwargs)
            context["user"] = CustomUser.objects.get(id=self.request.user.id)
            return context
        else:
            messages.error(self.request, "You are not allowed to edit this account.")
            return None

    def get_success_url(self):
        return reverse_lazy("order_history", kwargs={"pk": self.request.user.id})

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Details updated")
        return super().form_valid(form)


@login_required(login_url="login")
def order_view(request, order_id):
    ### given the UUId, gonna get the order
    ### will pass through the UUID if it is from django
    ### or an ID if it is from Odoo
    orderClient = OrderClient()
    # try:
    ## must be from django
    try:
        order_id = str(uuid.UUID(order_id))
        django = True
    except:
        order_id = int(order_id)
        django = False

    if django:
        ## don't need to access check here
        order = request.user.get_order(uuid=order_id)
        data = {
            "order_id": order_id,
            "order_number": order.purchase_order_ref or order.get_pleasant_id(),
            "customer_name": f"{order.customer.first_name} {order.customer.last_name}",
            "confirmation_date": "N/A",
            "client_order_ref": order.purchase_order_ref or order.get_pleasant_id(),
            "delivery_address": order.address_shipping_str,
        }
        data["subtotal"] = order.subtotal
        data["coupon"] = order.coupon
        data["coupon_value"] = order.coupon_value
        data["shipping_cost"] = order.shipping_cost
        data["admin_fee"] = order.admin_fee
        data["order_tax"] = order.order_tax
        # data["payment_type"] = order.payment_type
        data["order_surcharge"] = order.order_surcharge
        data["order_total"] = order.order_total

        order_items = [
            OrderItemOdooSerializer(
                **{
                    "product_name": x.get_product_name(),
                    "sku": x.get_product_sku(),
                    "product_quantity": x.product_quantity,
                    "qty_delivered": 0,
                    "product_price": x.product_price,
                }
            )
            for x in order.items.all()
        ]

        order_detail = OrderOdooSerializer(**data)
        fulfillments = []

    if not django:
        if request.user.get_group_code() == "TRADE":
            company_id = request.user.company_id.company_code
            order_detail, fulfillments = orderClient.get_order_detail(
                company_id=company_id, order_ids=[], odoo_id=order_id
            )

        if request.user.get_group_code() == "RETAIL":
            django_orders = request.user.get_orders()
            pleasant_ids = [x.get_pleasant_id() for x in django_orders]

            order_detail, fulfillments = orderClient.get_order_detail(
                company_id=None, order_ids=pleasant_ids, odoo_id=order_id
            )

        order_items = orderClient.get_order_items(order_id=order_detail.order_id)
        FREIGHT_SKUS = settings.FREIGHT_CODES
        ADMIN_FEE_SKUS = [settings.ADMIN_FEE_CODE]

        for oi in order_items:
            if oi.sku in FREIGHT_SKUS:
                order_detail.shipping_cost = oi.product_price
            elif oi.sku in ADMIN_FEE_SKUS:
                order_detail.admin_fee = oi.product_price
        order_items = [
            x for x in order_items if x.sku not in FREIGHT_SKUS and x.sku not in ADMIN_FEE_SKUS
        ]

    context = {
        "order_uuid": order_id,
        "order_items": order_items,
        "order": order_detail,
        "fulfillments": fulfillments,
    }
    return render(request, "account/order_view.html", context)


@CustomerReloadUps.register_class
class CustomerOrdersReload(BaseCustomerReload):
    class_name = "customer_orders"

    def get_context_data(self, request):
        post_data = request.data
        d = datetime.today() + timedelta(days=1)
        kwargs = {"from": "1970-01-01", "to": d.strftime("%Y-%m-%d"), "search_term": "%%"}
        search_temp = ""
        number_per_page = 20

        if "from" in post_data and post_data["from"] != None:
            kwargs["from"] = post_data["from"]
        if "to" in post_data and post_data["to"] != None:
            kwargs["to"] = post_data["to"]
        if "query" in post_data and post_data["query"] != "":
            kwargs["query"] = post_data["query"]
            search_temp = post_data["query"]

        kwargs["search_term"] = "%{}%".format(search_temp)

        page_number = post_data.get("page") if post_data.get("page") else 1
        offset = (page_number - 1) * number_per_page

        django_orders = request.user.get_orders(**kwargs)
        pleasant_ids = [x.get_pleasant_id() for x in django_orders]

        client = OrderClient()
        ## Get the orders outta odoo for the customer
        ## will use either the company code or a list of the order uuids
        if request.user.get_group_code() == "RETAIL":
            if len(pleasant_ids):
                num_odoo_orders, odoo_orders = client.get_orders_list(
                    False, pleasant_ids, offset, number_per_page, **kwargs
                )
            else:
                num_odoo_orders = 0
                odoo_orders = []

        elif request.user.get_group_code() == "TRADE":
            num_odoo_orders, odoo_orders = client.get_orders_list(
                request.user.company_id.company_code, [], offset, number_per_page, **kwargs
            )

        odoo_ords_by_id = {x["external_system_id"]: x for x in odoo_orders}
        order_items = []

        if request.user.get_group_code() == "RETAIL":
            ## used the uuid as lookup key, swaps out the django order for the odoo order
            for order in django_orders:
                if odoo_ords_by_id.get(order.get_pleasant_id()):
                    order_items.append(odoo_ords_by_id[order.get_pleasant_id()])
                else:
                    order_items.append(
                        {
                            "id": order.uuid,
                            "name": order.get_pleasant_id(),
                            "pleasant_id": order.get_pleasant_id(),
                            "create_date": order.create_date.strftime("%d/%m/%Y"),
                            "status": "Pending Confirmation",
                            "order_total": order.order_total,
                            "order_view_url": reverse(
                                "order_view", kwargs={"order_id": order.uuid}
                            ),
                        }
                    )
            ## used for pagination
            number_orders = len(django_orders)

        if request.user.get_group_code() == "TRADE":
            ### start with list from odoo, find any django ones which arent in there
            ### and append to the list
            django_orders_not_in_odoo = [
                x for x in django_orders if not odoo_ords_by_id.get(x.get_pleasant_id())
            ]
            order_items = odoo_orders
            for order in django_orders_not_in_odoo:
                ## adding arbitrary start date cos old data a bit junky
                status = (
                    "Pending Confirmation"
                    if order.create_date > datetime(2023, 1, 1).astimezone(tz=pytz.utc)
                    else "Shipped"
                )

                order_items.append(
                    {
                        "id": order.uuid,
                        "name": order.get_pleasant_id(),
                        "pleasant_id": order.get_pleasant_id(),
                        "create_date": order.create_date.strftime("%d/%m/%Y"),
                        "status": status,
                        "order_total": order.order_total,
                        "order_view_url": reverse("order_view", kwargs={"order_id": order.uuid}),
                    }
                )
            number_orders = num_odoo_orders + len(django_orders_not_in_odoo)

        num_pages = math.ceil(number_orders / number_per_page)
        page_obj = Page(page_number, number_per_page, num_pages)
        page_ranges = []

        for i in range(1, num_pages + 1):
            page_ranges.append(i)

        pagination = {
            "has_previous": page_obj.has_previous(),
            "previous_page_number": page_obj.previous_page_number()
            if page_obj.has_previous()
            else 0,
            "has_next": page_obj.has_next(),
            "next_page_number": page_obj.next_page_number() if page_obj.has_next() else 0,
            "number": page_obj.number,
            "previous_hellip": int(page_obj.number) - 4,
            "num_pages": num_pages,
            "next_hellip": int(page_obj.number) + 4,
            "page_ranges": page_ranges,
            "number_previous_hellip": int(page_obj.number) - 5,
            "number_next_hellip": int(page_obj.number) + 5,
        }

        context = {
            "orders": sorted(
                order_items,
                key=lambda x: datetime.strptime(x["create_date"], "%d/%m/%Y"),
                reverse=True,
            ),
            "pagination": pagination,
        }
        return context
