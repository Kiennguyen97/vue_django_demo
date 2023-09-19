import psycopg2 as Database
from psycopg2.extras import DictCursor

from customers.serializers import (
    OrderItemOdooSerializer,
    OrderOdooDelivery,
    OrderOdooSerializer,
)
from django.conf import settings
from django.urls import reverse, reverse_lazy


class OrderClient:
    def __init__(self):
        self.exclusions = (
            "Free Delivery",
            settings.CC_SURCHARGE_CODE,
            # settings.ADMIN_FEE_CODE,
            settings.CHOCOLATE_CODE,
        )

    def get_orders_list(self, company_id=None, ids_list=[], offset=0, limit=10, **kwargs):
        """gets list of orders for this customer. Depending on whether it is a
        trade user or a retail user, it will get all orders under the account,
        or orders that this user has placed
        """
        conn = Database.connect(settings.ODOO_DB_URI)
        cursor = conn.cursor(cursor_factory=DictCursor)
        query_count_str = """
            SELECT count(t1.*) as total FROM (
                SELECT a.id
                    FROM sale_order a
                    INNER JOIN res_partner b ON a.partner_id = b.id
                    INNER JOIN res_partner deliv ON a.partner_shipping_id = deliv.id
                    INNER JOIN sale_order_line c ON c.order_id = a.id
                    INNER JOIN product_product d ON c.product_id = d.id
                {filter}
                    AND d.default_code not in %(exclusions)s
                    AND a.state = 'sale'
                    AND (a.create_date >= %(from)s AND a.create_date <= %(to)s)
                    AND (
                        a.name ILIKE %(search_term)s
                        OR a.client_order_ref ILIKE %(search_term)s
                        OR a.external_system_id ILIKE %(search_term)s
                    )
                GROUP BY a.id
            ) AS t1
        """.format(
            filter="WHERE b.ref = %(_custcode)s"
            if company_id
            else "WHERE a.external_system_id IN %(ids_list)s"
        )

        cursor.execute(
            query_count_str,
            {
                "_custcode": company_id,
                "ids_list": tuple(ids_list),
                "exclusions": self.exclusions,
                "from": kwargs["from"],
                "to": kwargs["to"],
                "search_term": kwargs["search_term"],
            },
        )
        results_count = cursor.fetchone()
        total_number = results_count[0]

        order_items = []
        if total_number > 0:
            sql_string = """
                select a.id,
                a.name as order
                , TO_CHAR( (a.confirmation_date at time zone 'utc' at time zone 'Pacific/Auckland')::date, 'DD/MM/YYYY') AS date_confirmed
                , case when a.custom_delivery IS NOT NULL
                    THEN concat_ws(', ', b.name, a.custom_delivery)
                    ELSE concat_ws(', ',b.name, deliv.name,deliv.street,deliv.street2,deliv.city) 
                end as delivery_address
                , a.amount_total::float as total
                , case when sum(c.qty_invoiced) = sum(c.product_uom_qty) then 'Fully Shipped'
                    when sum(c.qty_delivered) = 0 then 'Unshipped'
                    else 'Partially Shipped'
                end as shipment_status
                , a.client_order_ref as order_number
                , a.external_system_id as external_system_id
                , TO_CHAR( (a.create_date at time zone 'utc' at time zone 'Pacific/Auckland')::date, 'DD/MM/YYYY') AS order_create_date
                from sale_order a
                join res_partner b
                on a.partner_id = b.id
                join res_partner deliv
                on a.partner_shipping_id = deliv.id
                join sale_order_line c
                on c.order_id = a.id
                join product_product d
                on c.product_id = d.id

                {filter}
                and d.default_code not in %(exclusions)s
                and a.state = 'sale'
                AND (a.create_date >= %(from)s AND a.create_date <= %(to)s)
                AND (
                        a.name ILIKE %(search_term)s
                        OR a.client_order_ref ILIKE %(search_term)s
                        OR a.external_system_id ILIKE %(search_term)s
                    )
                group by (
                    a.id
                    , a.confirmation_date
                    , a.create_date
                    , a.name
                    , a.client_order_ref
                    , deliv.name
                    , a.amount_total
                    , deliv.street
                    , deliv.street2
                    , deliv.city
                    , b.name
                    , a.custom_delivery
                    , a.external_system_id)

                order by a.confirmation_date DESC
                OFFSET %(offset)s
                limit %(limit)s
                ;
                """.format(
                filter="WHERE b.ref = %(_custcode)s"
                if company_id
                else "WHERE a.external_system_id IN %(ids_list)s"
            )

            cursor.execute(
                sql_string,
                {
                    "_custcode": company_id,
                    "ids_list": tuple(ids_list),
                    "exclusions": self.exclusions,
                    "from": kwargs["from"],
                    "to": kwargs["to"],
                    "search_term": kwargs["search_term"],
                    "offset": offset,
                    "limit": limit,
                },
            )
            order_result = cursor.fetchall()
            for x in order_result:
                item = dict(x)
                # print(item)
                order_items.append(
                    {
                        "id": item["id"],
                        "pleasant_id": item["order_number"]
                        if item["order_number"]
                        else item["external_system_id"],
                        "external_system_id": item["external_system_id"],
                        "create_date": item["order_create_date"],
                        "status": item["shipment_status"],
                        "order_total": round(item["total"], 2),
                        "order_view_url": reverse_lazy(
                            "order_view", kwargs={"order_id": item["id"]}
                        ),
                        "name": item["order"],
                    }
                )
        cursor.close()
        return total_number, order_items

    def get_order_detail(self, company_id=None, order_ids=[], odoo_id=None):
        """Gets order details from Odoo
        Includes access control by using either company_id or a specific list of orders
        Uses the order_id to get the specific order by sale_order.id
        """

        conn = Database.connect(settings.ODOO_DB_URI)
        cursor = conn.cursor(cursor_factory=DictCursor)
        query_str = """
            SELECT 
                o.id as order_id,
                o.name as order_number,
                CONCAT('(',res.ref,') ', res.name) as customer_name,
                TO_CHAR(
                    (o.confirmation_date at time zone 'utc' 
                        at time zone 'Pacific/Auckland')::date, 
                    'DD/MM/YYYY') AS confirmation_date,
                o.client_order_ref as client_order_ref,
                CASE
                    WHEN o.custom_delivery is not null
                    THEN o.custom_delivery
                    ELSE concat_ws(', ',deliv.street,deliv.street2,deliv.city) 
                END as delivery_address ,
                o.amount_total::float as order_total,
                o.amount_untaxed::float as subtotal,
                o.amount_tax::float as order_tax,
                ARRAY(
                    SELECT JSON_BUILD_OBJECT(
                        'name', stp.name
                        , 'tracking_ref', stp.carrier_tracking_ref
                    )
                    FROM stock_picking stp
                    WHERE stp.origin=o.name
                    AND stp.state = 'done'
                    AND stp.picking_type_id=4
                ) as deliv_array
            FROM sale_order o
            LEFT JOIN res_partner res ON o.partner_id = res.id
            LEFT JOIN res_partner deliv ON o.partner_shipping_id = deliv.id
            {filter}
            AND o.id = %(id)s
        """.format(
            filter="WHERE res.ref = %(company_id)s"
            if company_id
            else "WHERE o.external_system_id IN %(order_ids)s"
        )

        cursor.execute(
            query_str, {"id": odoo_id, "company_id": company_id, "order_ids": tuple(order_ids)}
        )
        order_detail = cursor.fetchone()
        cursor.close()

        data = dict(order_detail)

        data["coupon"] = ""
        data["coupon_value"] = 0
        data["shipping_cost"] = 0
        data["admin_fee"] = 0
        data["order_surcharge"] = 0

        fulfillments = []
        for x in order_detail["deliv_array"]:
            fulfillments.append(OrderOdooDelivery(name=x["name"], tracking_link=x["tracking_ref"]))

        data.pop("deliv_array")

        return OrderOdooSerializer(**data), fulfillments

    def get_order_items(self, order_id=None):
        conn = Database.connect(settings.ODOO_DB_URI)
        cursor = conn.cursor(cursor_factory=DictCursor)

        query_str = """
            SELECT 
                TRIM(p.default_code) as sku,
                e.name as product_name,
                oi.product_uom_qty::float as product_quantity,
                oi.qty_invoiced::float as qty_delivered,
                oi.price_unit::float as product_price
            FROM sale_order_line oi
            INNER JOIN product_product p on oi.product_id = p.id
            INNER JOIN product_template e ON p.product_tmpl_id = e.id
            WHERE oi.order_id = %(order_id)s
            AND p.default_code not in %(exclusions)s
        """
        cursor.execute(query_str, {"order_id": order_id, "exclusions": self.exclusions})
        order_lines = cursor.fetchall()
        cursor.close()
        order_items = [OrderItemOdooSerializer(**dict(x)) for x in order_lines]
        return order_items

    def get_skus(self, order_id=None):
        # get all order items from Odoo

        conn = Database.connect(settings.ODOO_DB_URI)
        cursor = conn.cursor(cursor_factory=DictCursor)

        query_str = """
            SELECT 
                TRIM(p.default_code) as sku,
                oi.product_uom_qty::float as product_quantity
            FROM sale_order_line oi
            INNER JOIN product_product p on oi.product_id = p.id
            INNER JOIN product_template e ON p.product_tmpl_id = e.id
            WHERE oi.order_id = %(order_id)s
                AND p.default_code not in %(exclusions)s
        """
        cursor.execute(query_str, {"order_id": order_id, "exclusions": self.exclusions})

        order_lines = cursor.fetchall()
        cursor.close()
        items = {}
        for x in order_lines:
            obj = dict(x)
            items[obj["sku"]] = obj["product_quantity"]
        return items
