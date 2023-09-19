import math

import psycopg2 as Database
import psycopg2.extras

from customers.account import BaseCustomerReload, CustomerReloadUps, Page
from customers.models import CustomUser
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView


@method_decorator(login_required, name="dispatch")
class Backorder(ListView):
    model = CustomUser
    template_name = "account/backorder.html"


@CustomerReloadUps.register_class
class CustomerBackorderReload(BaseCustomerReload):
    class_name = "customer_backorder"

    def get_context_data(self, request):
        def get_backourders_with_time_range(
            cursor, ref, search_temp, from_date, to_date, offset, per_page
        ):
            query_count_str = """
                SELECT count(pt.default_code) 
                FROM stock_move stm
                LEFT JOIN product_product pp on stm.product_id = pp.id
                LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                LEFT JOIN stock_picking stp on stm.picking_id = stp.id
                LEFT JOIN sale_order so ON so.name = stp.origin
                LEFT JOIN res_partner rp on so.partner_id = rp.id
                LEFT JOIN res_partner deliv on so.partner_shipping_id = deliv.id
                WHERE stm.state in ('waiting','confirmed','assigned')
                    AND stp.backorder_id IS NOT NULL
                    AND pt.default_code != 'NoteSO' 
                    AND rp.ref = %(ref)s
                    AND (
                        pt.default_code ILIKE %(search_temp)s
                        OR pt.name ILIKE %(search_temp)s
                        OR stm.origin ILIKE %(search_temp)s
                    )
                    AND (stm.create_date >= %(from)s AND stm.create_date <= %(to)s)
            """
            cursor.execute(
                query_count_str,
                {
                    "ref": ref,
                    "search_temp": search_temp,
                    "from": from_date,
                    "to": to_date,
                },
            )
            results_count = cursor.fetchone()
            if int(results_count[0]) > 0:
                query_str = """SELECT 
                    pt.default_code as sku
                    , pt.name as product_name
                    , stm.product_uom_qty::float AS product_qty
                    , stm.origin AS so_numbner
                    , TO_CHAR(
                        stm.create_date::date at time zone 'utc' 
                        at time zone 'Pacific/Auckland', 'DD/MM/YYYY') AS create_date
                    , CASE
                        when so.custom_delivery IS NOT NULL
                            THEN concat_ws(', ', rp.name, so.custom_delivery)
                            ELSE concat_ws(', ',rp.name, deliv.name,deliv.street,deliv.street2,deliv.city) 
                        END AS delivery_address
                    FROM
                    stock_move stm
                    LEFT JOIN product_product pp on stm.product_id = pp.id
                    LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                    LEFT JOIN stock_picking stp on stm.picking_id = stp.id
                    LEFT JOIN sale_order so ON so.name = stp.origin
                    LEFT JOIN res_partner rp on so.partner_id = rp.id
                    LEFT JOIN res_partner deliv on so.partner_shipping_id = deliv.id
                    WHERE stm.state in ('waiting','confirmed','assigned')
                        AND stp.backorder_id IS NOT NULL
                        AND pt.default_code != 'NoteSO'
                        AND rp.ref = %(ref)s
                        AND (
                            pt.default_code ILIKE %(search_temp)s
                            OR pt.name ILIKE %(search_temp)s
                            OR stm.origin ILIKE %(search_temp)s
                        )
                        AND (stm.create_date >= %(from)s AND stm.create_date <= %(to)s)
                    ORDER BY stm.create_date
                    OFFSET %(offset)s
                    LIMIT %(limit)s
                """

                cursor.execute(
                    query_str,
                    {
                        "ref": ref,
                        "search_temp": search_temp,
                        "from": from_date,
                        "to": to_date,
                        "offset": offset,
                        "limit": per_page,
                    },
                )
                results = cursor.fetchall()
                return int(results_count[0]), results
            return 0, {}

        def get_backourders_without_time_range(cursor, ref, search_temp, offset, per_page):
            query_count_str = """
                SELECT count(pt.default_code) 
                FROM stock_move stm
                LEFT JOIN product_product pp on stm.product_id = pp.id
                LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                LEFT JOIN stock_picking stp on stm.picking_id = stp.id
                LEFT JOIN sale_order so ON so.name = stp.origin
                LEFT JOIN res_partner rp on so.partner_id = rp.id
                LEFT JOIN res_partner deliv on so.partner_shipping_id = deliv.id
                WHERE stm.state in ('waiting','confirmed','assigned')
                    AND stp.backorder_id IS NOT NULL
                    AND pt.default_code != 'NoteSO' 
                    AND rp.ref = %(ref)s
                    AND (
                        pt.default_code ILIKE %(search_temp)s
                        OR pt.name ILIKE %(search_temp)s
                        OR stm.origin ILIKE %(search_temp)s
                    )
            """
            cursor.execute(
                query_count_str,
                {
                    "ref": ref,
                    "search_temp": search_temp,
                },
            )
            results_count = cursor.fetchone()
            if int(results_count[0]) > 0:
                query_str = """SELECT 
                    pt.default_code as sku
                    , pt.name as product_name
                    , stm.product_uom_qty::float AS product_qty
                    , stm.origin AS so_numbner
                    , TO_CHAR(
                        stm.create_date::date at time zone 'utc' 
                        at time zone 'Pacific/Auckland', 'DD/MM/YYYY') AS create_date
                    , CASE
                        when so.custom_delivery IS NOT NULL
                            THEN concat_ws(', ', rp.name, so.custom_delivery)
                            ELSE concat_ws(', ',rp.name, deliv.name,deliv.street,deliv.street2,deliv.city) 
                        END AS delivery_address
                    FROM
                    stock_move stm
                    LEFT JOIN product_product pp on stm.product_id = pp.id
                    LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                    LEFT JOIN stock_picking stp on stm.picking_id = stp.id
                    LEFT JOIN sale_order so ON so.name = stp.origin
                    LEFT JOIN res_partner rp on so.partner_id = rp.id
                    LEFT JOIN res_partner deliv on so.partner_shipping_id = deliv.id
                    WHERE stm.state in ('waiting','confirmed','assigned')
                        AND stp.backorder_id IS NOT NULL
                        AND pt.default_code != 'NoteSO'
                        AND rp.ref = %(ref)s
                        AND (
                            pt.default_code ILIKE %(search_temp)s
                            OR pt.name ILIKE %(search_temp)s
                            OR stm.origin ILIKE %(search_temp)s
                        )
                    ORDER BY stm.create_date
                    OFFSET %(offset)s
                    LIMIT %(limit)s
                """

                cursor.execute(
                    query_str,
                    {
                        "ref": ref,
                        "search_temp": search_temp,
                        "offset": offset,
                        "limit": per_page,
                    },
                )
                results = cursor.fetchall()
                return int(results_count[0]), results
            return 0, {}

        per_page = 10
        post_data = request.data
        ref = request.user.company_id.company_code

        if not ref:
            return False

        # Connect DB of ODOO
        conn = Database.connect(settings.ODOO_DB_URI)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        items = []
        pagination = {}
        page_number = post_data.get("page") if post_data.get("page") else 1
        offset = (page_number - 1) * per_page
        search_temp = post_data.get("search_temp") if post_data.get("search_temp") else ""
        search_temp = "%{}%".format(search_temp)

        if post_data.get("from"):
            from_date = post_data.get("from")
            to_date = post_data.get("to")
            results_count, results = get_backourders_with_time_range(
                cursor, ref, search_temp, from_date, to_date, offset, per_page
            )
        else:
            results_count, results = get_backourders_without_time_range(
                cursor, ref, search_temp, offset, per_page
            )

        if results_count > 0:
            for item in results:
                items.append(dict(item))

            num_pages = math.ceil(results_count / per_page)
            page_obj = Page(page_number, per_page, num_pages)

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

        cursor.close()
        context = {"items": items, "pagination": pagination}
        return context
