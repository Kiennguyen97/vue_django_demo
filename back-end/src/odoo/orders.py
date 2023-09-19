import traceback
from datetime import datetime, timedelta
from functools import lru_cache

import erppeek

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from odoo.odoo_client import OdooClient as client
from products.models_order import Order, OrderItem
from products.utils import smtp_send


def send_email_issue(order, e):
    smtp_send(
        subject=f"Issue importing order {order.get_pleasant_id()}",
        emails=[settings.EMAIL_CC],
        body=order.uuid + "\n" + str(e),
    )
    return True


def check_if_in_odoo(pleasant_id, uuid):
    orders_list = client.Instance().count("sale.order", [("external_system_id", "=", pleasant_id)])
    if orders_list == 0:
        return False  # not there
    else:
        return True  # is already there


@lru_cache()
def get_res_partner(cust_number, delivery_id=False):
    res = client.Instance().ResPartner.search_read(
        [["ref", "=", cust_number]],
        [
            "id",
            "property_product_pricelist",
            "child_ids",
            "property_delivery_carrier_id",
            "no_admin_fee",
        ],
    )[0]
    partner_id = res["id"]
    pricelist_id = res["property_product_pricelist"][0]
    child_ids = res["child_ids"]

    invoice_id = client.Instance().ResPartner.search(
        [["id", "in", child_ids], ["type", "=", "invoice"]]
    )[0]

    if not delivery_id:
        delivery_id = client.Instance().ResPartner.search(
            [["id", "in", child_ids], ["type", "=", "delivery"]],
        )[0]

    if not res["property_delivery_carrier_id"]:
        carrier = 3
    else:
        carrier = res["property_delivery_carrier_id"][0]
    no_admin_fee = True if res["no_admin_fee"] == True else False
    return partner_id, pricelist_id, invoice_id, delivery_id, carrier, no_admin_fee


@lru_cache()
def get_odoo_product_id(code):
    prod_id = client.Instance().ProductProduct.search([("default_code", "=", code)])
    if not prod_id:
        raise
    else:
        return prod_id[0]


def get_delivery(order):
    # get nice shipping address
    if not order.address_shipping.odoo_id:
        prepend = ""
        try:
            shipping_address = order.address_shipping.get_display_str_line_br()
        except:
            shipping_address = order.address_shipping_str.replace(", ", "\n")
            prepend += f"{order.customer.first_name} {order.customer.last_name}\n"

        if order.customer.company_name:
            prepend += f"{order.customer.company_name}\n"

        return prepend + shipping_address
    else:
        return order.address_shipping.odoo_id


def send_order_stuck_notification(order):
    from django.conf import settings
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    subject = f"Order Processing Issue - {order.get_pleasant_id()}"
    html_content = render_to_string(
        "mail_order_stuck_notification.html",
        {
            "order_obj": order,
            "order_items": order.items.all(),
            "BASE_URL": settings.BASE_URL,
            "STATIC_URL": settings.STATIC_URL,
        },
    )
    plain_message = strip_tags(html_content)
    smtp_send(
        subject=subject,
        emails=[settings.EMAIL_CC],
        body=plain_message,
        html_body=html_content,
    )
    order.odoo_is_imported = True
    order.save()


def validate_than_six_hours(order):
    time_filter = timezone.now() - timedelta(hours=6)
    create_at = order.create_date
    if create_at < time_filter:
        return True
    return False


def submit_odoo_order(order):

    ## if it's already there, return false and tick as done
    ## double check measure to make sure we don't double up
    if check_if_in_odoo(order.get_pleasant_id(), order.uuid):
        order.odoo_is_imported = True
        order.save()
        return False

    # if it's older than 6 hours, send stuck notification and return false
    if validate_than_six_hours(order):
        send_order_stuck_notification(order)
        return False

    # get company number
    if order.payment_type == "c_d_card":
        company_number = settings.CREDIT_CARD_ACCOUNT
        confirm_order = False
    elif order.payment_type == "d_d":
        company_number = settings.DIRECT_DEBIT_ACCOUNT
        confirm_order = False
    elif order.payment_type == "credit":
        confirm_order = False
        company_number = order.company_id.company_code
    try:
        (
            partner_id,
            pricelist_id,
            invoice_id,
            shipping_id,
            carrier_id,
            no_admin_fee,
        ) = get_res_partner(company_number)
    except Exception as e:
        order.odoo_is_imported = True
        order.save()
        print("ERRROR", traceback.format_exc())
        mgs = (
            "Customer email: %s \nCompany name: %s \nCompany code: %s \n"
            "The customer cannot be found in Odoo, maybe they may have been archived. Please key this order manually \n"
            % (
                order.customer.email,
                order.company_id.name,
                order.company_id.company_code,
            )
        )

        send_email_issue(order, mgs)
        return False

    ### TODO  - need to work out what to do around custom deliveries etc

    delivery = get_delivery(order)
    po_number = order.purchase_order_ref or order.get_pleasant_id()

    odoo_order_items = []
    order_items_obj = OrderItem.objects.filter(order_uuid=order.uuid)
    for item in order_items_obj:
        order_item = {
            "qty": item.product_quantity,
            "code": item.product.sku,
            "price_unit": item.product_price,
            "name": item.product.name,
            "product_id": get_odoo_product_id(item.product.sku),
            "item": item,
        }
        odoo_order_items.append(order_item)

    try:
        create_odoo_order(
            order=order,
            partner_id=partner_id,
            shipping_id=shipping_id,
            invoice_id=invoice_id,
            order_note=order.order_notes,
            pricelist_id=pricelist_id,
            carrier_id=carrier_id,
            delivery=delivery,  # this will be int of odoo_id or str of custom_delivery
            po_number=po_number,
            external_system_id=order.get_pleasant_id(),
            confirm_order=confirm_order,
            surcharge=order.order_surcharge,
            order_total=order.order_total,
            items=odoo_order_items,
            no_admin_fee=no_admin_fee,
        )

        order.odoo_is_imported = True
        order.save()

    except Exception as e:
        print("ERRROR", traceback.format_exc())
        send_email_issue(order, traceback.format_exc())

    return True


def create_odoo_order(
    order,
    partner_id,
    shipping_id,
    invoice_id,
    order_note,
    pricelist_id,
    carrier_id,
    delivery,
    po_number,
    external_system_id,
    confirm_order,
    surcharge,
    order_total,
    items,
    no_admin_fee,
):

    so_dict = {
        "partner_id": partner_id,
        "partner_invoice_id": invoice_id,
        "order_note": order_note,
        "pricelist_id": pricelist_id,
        "order_source_id": settings.ORDER_SOURCE_ID,
        "carrier_id": carrier_id,
        "client_order_ref": po_number,
        "external_system_id": external_system_id,
        "payment_term_id": 5,  ## 20F
        "picking_policy": "direct",  ## each product when available
        "is_warn": True,  ## old tickbox, don't think we use.
    }
    if isinstance(delivery, int):
        so_dict["partner_shipping_id"] = delivery
    else:
        so_dict["partner_shipping_id"] = shipping_id
        so_dict["custom_delivery"] = delivery

    so_id = client.Instance().SaleOrder.create(so_dict)
    order.odoo_id = so_id.id
    tax_tuple = (4, 1, 0)
    for item in items:
        item_id = client.Instance().SaleOrderLine.create(
            {
                "order_id": so_id,
                "product_id": item["product_id"],
                "product_uom_qty": item["qty"],
                "price_unit": item["price_unit"],
                "tax_id": [tax_tuple],
            }
        )
        order_item = item["item"]
        order_item.odoo_id = item_id.id
        order_item.save()

    if surcharge != 0:
        surcharge_tuple = (4, 2, 0)
        product_id = get_odoo_product_id(settings.CC_SURCHARGE_CODE)
        client.Instance().SaleOrderLine.create(
            {
                "order_id": so_id,
                "product_id": product_id,
                "product_uom_qty": 1,
                "price_unit": surcharge,
                "tax_id": [surcharge_tuple],
            }
        )

    if not no_admin_fee:
        product_id = get_odoo_product_id(settings.ADMIN_FEE_CODE)
        client.Instance().SaleOrderLine.create(
            {
                "order_id": so_id,
                "product_id": product_id,
                "product_uom_qty": 1,
                "price_unit": settings.ADMIN_FEE_PRICE,
                "tax_id": [tax_tuple],
            }
        )

    if order_total > settings.CHOCOLATE_THRESHOLD:
        product_id = get_odoo_product_id(settings.CHOCOLATE_CODE)
        client.Instance().SaleOrderLine.create(
            {
                "order_id": so_id,
                "product_id": product_id,
                "product_uom_qty": 1,
                "product_uom": 1,
                "price_unit": 0,
                "tax_id": [tax_tuple],
            }
        )

    if confirm_order:
        so_id.action_confirm()

    odoo_order_total = so_id.amount_total

    if int(odoo_order_total - order_total) != 0:
        odoo_inc_ship = odoo_order_total + settings.SHIPPING_FLAT_RATE * (1 + settings.GST_RATE)
        if int(odoo_inc_ship - order_total) != 0:
            smtp_send(
                subject=f"Website Pricing Issue on order {external_system_id}",
                emails=[settings.EMAIL_CC],
                body=f"Odoo Order Total - ${odoo_order_total}<br/>Django Order Total ${order_total}",
            )

    return JsonResponse({"success": True})
