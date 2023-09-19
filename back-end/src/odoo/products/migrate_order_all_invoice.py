import datetime as dt
import uuid
from pprint import pprint as pp

import psycopg2 as Database
import pytz
from dateutil.relativedelta import relativedelta
from psycopg2.extras import DictCursor

from django.conf import settings
from django.db.models import CharField, Value
from django.db.models.expressions import F, Q
from django.db.models.functions import Concat, Substr
from odoo.utils import (
    _get_model,
    bulk_create,
    bulk_delete,
    bulk_delete_multiple_fields,
    bulk_update,
    check_length_fields,
    requires_update,
)

uu = lambda: str(uuid.uuid4())


def get_order_invoices(conn):
    ## toggle to do a full flush
    FULL = False

    cursor = conn.cursor(cursor_factory=DictCursor)
    query_str = """
        SELECT distinct on 
        (a.id, a.date_invoice)
            a.id as invoice_id,
            so.id as order_id,
            so.external_system_id,
            a.number,
            a.amount_untaxed::float as total_exc_gst,
            (a.amount_untaxed + a.amount_tax)::float as total_inc_gst,
            a.amount_untaxed,
            a.name, 
            a.origin,
            a.date_invoice,
            a.date_due,
            a.state,
            rp.ref,
            ir.store_fname,
            ir.mimetype,
            a.create_date
        FROM account_invoice a 
        INNER JOIN sale_order so ON so.name = a.origin
        LEFT JOIN res_partner rp ON so.partner_id = rp.id 
        LEFT JOIN ir_attachment ir 
            ON ir.res_id = a.id 
            AND ir.res_model = 'account.invoice' 
            AND ir.mimetype = 'application/pdf'
        WHERE a.state IN ('open','paid')
            AND a.type IN ('out_invoice', 'out_refund')
    """

    if not FULL:
        query_str += " AND ( a.date_invoice >= NOW() - INTERVAL '1 WEEK' OR a.write_date >= NOW() - INTERVAL '1 Week' )"
    elif FULL:
        query_str += " AND a.date_invoice >= NOW() - INTERVAL '2 YEARS'"

    query_str += "ORDER BY a.id, a.date_invoice DESC"

    cursor.execute(query_str)
    items = [dict(x) for x in cursor.fetchall()]
    cursor.close()
    return items


def create_pdf_url(obj):
    """Create pdf name for invoice, return string"""
    fname = obj["store_fname"][0:10]
    ext = obj["mimetype"].split("/")[1]
    return fname + "." + ext


def execute():
    """Main Function"""
    # Connect DB of ODOO
    conn = Database.connect(settings.ODOO_DB_URI)

    c_d_card_and_d_d_ref = [settings.CREDIT_CARD_ACCOUNT, settings.DIRECT_DEBIT_ACCOUNT]
    order_refs = []
    external_system_ids = []
    invoice_objs = {}
    ref_invoice_objs = {}

    OrderModel = _get_model("products.order")
    InvoiceModel = _get_model("products.OrderInvoice")
    CompModel = _get_model("customers.company")

    invoice_items = get_order_invoices(conn)
    state_dict = {"open": "Unpaid", "paid": "Paid"}

    all_companies = {x.company_code: x for x in CompModel.objects.all()}
    all_invoices = {}

    for x in InvoiceModel.objects.all():
        all_invoices[x.odoo_id] = x

    invoice_in_objs = []
    invoice_up_objs = []
    i = 0
    k = 0

    def is_cash(obj, all_c):
        if all_companies.get(obj["ref"]) and obj["ref"] not in c_d_card_and_d_d_ref:
            return False  ## not cash
        return True  ## is cash

    def gen_pdf_url(obj):
        if obj["store_fname"]:
            obj["pdf_url"] = create_pdf_url(obj)
        else:
            obj["pdf_url"] = ""
        return obj

    for obj in invoice_items:
        try:
            ## check its not a cash sale invoice
            if not is_cash(obj, all_companies):
                ## and that this invoice is not currently in the database.
                obj = gen_pdf_url(obj)
                if not all_invoices.get(obj["invoice_id"]):
                    comp = all_companies[obj["ref"]]

                    pk = uu()
                    invoice_data = {
                        "uuid": pk,
                        "name": obj["number"],
                        "company_id_id": comp.uuid,
                        # "customer_id_id": order.customer_id,
                        "odoo_id": obj["invoice_id"],
                        "total_exc_gst": obj["total_exc_gst"],
                        "total_inc_gst": obj["total_inc_gst"],
                        "date_invoice": obj["date_invoice"],
                        "due_date": obj["date_due"],
                        "payment_status": state_dict[obj["state"].lower()],
                        "invoice_source": obj["origin"],
                        "pdf_url": obj["pdf_url"],
                    }
                    print(f"Create new the order invoice - {obj['number']}")
                    invoice_data[InvoiceModel._meta.pk.attname] = pk
                    invoice_in_objs.append(InvoiceModel(**invoice_data))
                    i += 1
                else:  # we update existing invoice
                    existing_obj = all_invoices[obj["invoice_id"]]
                    payment_status = state_dict[obj["state"].lower()]
                    name = existing_obj.name

                    update = False
                    if existing_obj.payment_status != payment_status:
                        update = True
                        print(
                            name,
                            "payment_status",
                            "needs updating from ",
                            existing_obj.payment_status,
                            "to",
                            payment_status,
                        )

                        existing_obj.payment_status = payment_status

                    if existing_obj.pdf_url != obj["pdf_url"]:
                        update = True
                        print(
                            name,
                            "pdf_url",
                            "needs updating from ",
                            existing_obj.pdf_url,
                            "to",
                            obj["pdf_url"],
                        )
                        existing_obj.pdf_url = obj["pdf_url"]

                    if update == True:
                        invoice_up_objs.append(existing_obj)
                        k += 1

        except Exception as e:
            print(e)
            raise e

    bulk_create(InvoiceModel, invoice_in_objs, i, "Order Invoice")
    bulk_update(InvoiceModel, invoice_up_objs, ["payment_status"], k, "Order Invoice")
