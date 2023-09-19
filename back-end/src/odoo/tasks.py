import base64
import csv
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

import django_rq
import erppeek
import psycopg2
from psycopg2.extras import DictCursor

from django.conf import settings
from django.db.models import Count
from django.http import HttpResponse
from django.templatetags.static import static
from django.utils import timezone
from django.utils.timezone import make_aware
from odoo.utils import bulk_update
from products.models import Product
from products.models_order import (
    Order,
    OrderFulfillment,
    OrderFulfillmentItem,
    OrderInvoice,
    OrderItem,
)

# from products.tasks import send_order_invoice, send_shipping_confirmation
# from .get_odoo_invoice import retrieve_invoice_from_cache, retrieve_odoo_invoice
from .orders import submit_odoo_order


def enqueue_order(order):
    ## check if the order is already in the job queue
    existing_jobs = django_rq.get_queue("low").job_ids
    if order.uuid not in existing_jobs:
        ## as soon as the worker pops the
        # job out, it will not be in the job_ids
        django_rq.get_queue("low").enqueue(submit_odoo_order, order, job_id=order.uuid)


def sync_order_to_odoo():
    orders = (
        Order.objects.select_related("customer")
        .select_related("company_id")
        .filter(odoo_is_imported=False, status="order")
        .order_by("create_date")
    )

    if orders:
        for order in orders:
            enqueue_order(order)
    else:
        print("No Orders to procezzz")
    return HttpResponse("success")


# def sync_fulfillment_to_django():
#     conn = psycopg2.connect(settings.ODOO_DB_URI)
#     cursor = conn.cursor(cursor_factory=DictCursor)
#     sql = """
#         SELECT stp.name as shipping_name
#         , so.external_system_id as order_id
#         , so.partner_id
#         , ptm.default_code
#         , SUM(stm.product_uom_qty) as qty_shipped
#         , stp.date_done as date_shipped
#         FROM stock_move stm
#         LEFT JOIN stock_picking stp on stm.picking_id = stp.id
#         LEFT JOIN sale_order so on stp.origin = so.name
#         LEFT JOIN res_partner rp on so.partner_id = rp.id
#         LEFT JOIN product_product pp on stm.product_id = pp.id
#         LEFT JOIN product_template ptm on pp.product_tmpl_id = ptm.id
#         WHERE stp.date_done > (NOW() - Interval '6 Hours')
#         AND stp.state = 'done'
#         AND stm.state = 'done'
#         AND stp.picking_type_id = 4
#         AND rp.ref in %(partner_id)s
#         AND so.external_system_id IS NOT NULL
#         GROUP BY
#             (
#                 stp.name
#                 , so.external_system_id
#                 , so.partner_id
#                 , ptm.default_code
#                 , stp.date_done
#             )
#         ;
#         """

#     cursor.execute(
#         sql,
#         {"partner_id": (settings.CREDIT_CARD_ACCOUNT, settings.DIRECT_DEBIT_ACCOUNT)},
#     )
#     results = [dict(x) for x in cursor.fetchall()]

#     # loop through the above.
#     # check that a fulfillment is not already created for this order
#     # if necessary, create a new fulfillment and send the email
#     # create mock values for the carrier etc.
#     # will need to run on a cron every hour.

#     fulfillments = defaultdict(list)
#     for item in results:
#         fulfillments[item["shipping_name"]].append(item)

#     from pprint import pprint as pp

#     pp(fulfillments)
#     for _, el in fulfillments.items():
#         order_uuid = el[0]["order_id"].split("#")[1]
#         try:
#             order = Order.objects.get(uuid=order_uuid)
#         except:
#             order = None

#         if order:
#             if not OrderFulfillment.objects.filter(
#                 order_id=order.uuid, shipping_name=el[0]["shipping_name"]
#             ).exists():
#                 order_fulfill = OrderFulfillment(
#                     order_id=order,
#                     customer_id=order.customer,  # trade or retal
#                     date_shipped=el[0]["date_shipped"],
#                     carrier_name="Post Haste",
#                     carrier_tracking_url="https://posthaste.co.nz/phl/servlet/ITNG_TAndTServlet?page=1&Key_Type=CustomerLabel&VCCA=Enabled&customer_number=0112505&consignment_id=D"
#                     + el[0]["shipping_name"].split("/")[-1],
#                     shipping_name=el[0]["shipping_name"],
#                 )
#                 order_fulfill.save()

#                 ### gather the items and add them to the fulfillment object
#                 for fulfillment_line in el:

#                     if fulfillment_line["default_code"] == "DI1070":
#                         sku = "RAT-R-25"
#                     else:
#                         sku = fulfillment_line["default_code"]

#                     product = Product.objects.get(sku=sku)

#                     item = OrderFulfillmentItem(
#                         qty_shipped=int(fulfillment_line["qty_shipped"]),
#                         product_id=product,
#                     )
#                     item.save()
#                     order_fulfill.items.add(item)

#                 order_fulfill.save()
#                 send_shipping_confirmation.delay(order_fulfill)
#             else:
#                 pass

#     return HttpResponse("success")


# def check_if_invoice_exist(fulfill):
#     stock_pick = client.search_read(
#         "stock.picking",
#         [("name", "=", fulfill.shipping_name)],
#         ["id", "invoice_id"],
#     )
#     if stock_pick:
#         invoice_id = stock_pick[0]["invoice_id"]
#         if invoice_id:
#             invoice = client.search_read(
#                 "account.invoice",
#                 [("id", "=", invoice_id[0]), ("state", "in", ("open", "paid"))],
#                 [
#                     "amount_untaxed",
#                     "amount_total",
#                     "number",
#                     "name",
#                     "date_invoice",
#                 ],
#             )
#             print("INVOICE EXISTS", invoice)
#             return invoice
#         else:
#             return False
#     else:
#         return False


# def add_job_invoice(fulfill):
#     invoice_uuid = str(uuid.uuid4())
#     invoice = check_if_invoice_exist(fulfill)
#     if invoice:
#         ## check that invoice is not already created in django
#         if not OrderInvoice.objects.filter(name=invoice[0]["number"].replace("/", "-")):

#             # try get it from the cache
#             ba64 = retrieve_invoice_from_cache(client, invoice[0]["id"], invoice_uuid)
#             # if not ba64:
#             #     # else render it from using the hacky scrape
#             #     retrieve_odoo_invoice(invoice[0]['id'], invoice_uuid)

#             if ba64:
#                 ## create an object to store it
#                 order_inv = OrderInvoice(
#                     uuid=invoice_uuid,
#                     name=invoice[0]["number"].replace("/", "-"),
#                     customer_id=fulfill.customer_id,
#                     odoo_id=invoice[0]["id"],
#                     total_exc_gst=invoice[0]["amount_untaxed"],
#                     total_inc_gst=invoice[0]["amount_total"],
#                     due_date=make_aware(
#                         datetime.strptime(invoice[0]["date_due"], "%Y-%m-%d")
#                     ),
#                     invoice_source=invoice[0]["origin"],
#                     date_invoice=make_aware(
#                         datetime.strptime(invoice[0]["date_invoice"], "%Y-%m-%d")
#                     ),
#                     customer_po=invoice[0]["name"],
#                     payment_status="PAID"  ### if you change this
#                     # , will have to have some way
#                     # to update them when they become paid....
#                 )
#                 if fulfill.customer_id.get_group_code() == "TRADE":
#                     order_inv.company_id = fulfill.customer_id.company_id
#                 order_inv.save()
#                 send_order_invoice(order_inv)


# def enqueue_order_fulfillments(orderf):
#     existing_jobs = django_rq.get_queue("low").job_ids
#     if orderf not in existing_jobs:
#         django_rq.get_queue("low").enqueue(
#             add_job_invoice, args=(orderf,), job_id=orderf.uuid
#         )


# def sync_invoice_to_django():
#     end_date = timezone.now()
#     start_date = end_date - timedelta(days=8)
#     fulfills = OrderFulfillment.objects.filter(
#         create_date__range=(start_date, end_date)
#     )

#     if fulfills:
#         for fulfill in fulfills:
#             enqueue_order_fulfillments(fulfill)

#     return HttpResponse("success")


def update_product_order():

    month_ago = timezone.now() - timedelta(days=31)
    all_products = Product.objects.all()
    order_count = (
        OrderItem.objects.filter(order__create_date__gt=month_ago)
        .values("product")
        .annotate(c=Count("product"))
        .order_by("-c")
        .all()
    )

    count_per_product = {x["product"]: x["c"] for x in order_count}

    ### manually do height safety for the first month, remove this later ###
    with open("hs_sales.csv") as f:
        csv_r = csv.reader(f)
        for row in csv_r:
            try:
                count_per_product[row[0]] = int(row[1]) / 24  # have 24months data in the sheet
            except Exception as e:
                print(e)
                pass

    to_update = []
    for item in all_products:
        if item.ordering != count_per_product.get(item.sku, 0):
            item.ordering = count_per_product.get(item.sku, 0)
            to_update.append(item)

    bulk_update(Product, to_update, ["ordering"], len(to_update), "product_ordering")


def sentry_with_failed_job():
    import django_rq
    from rq.job import Job
    from rq.registry import FailedJobRegistry
    from sentry_sdk import capture_message

    queue = django_rq.get_queue("default")
    connection = queue.connection
    registry = FailedJobRegistry(queue=queue)

    # This is how to remove a job from a registry
    for job_id in registry.get_job_ids():
        job = Job.fetch(job_id, connection=connection)
        capture_message(job.exc_info)
