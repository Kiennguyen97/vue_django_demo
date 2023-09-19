import os
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pprint import pprint as pp

import mysql.connector

from django.db import DEFAULT_DB_ALIAS, connection, transaction
from odoo.utils import (
    _get_model,
    bulk_create,
    bulk_delete,
    bulk_update,
    check_length_fields,
    get_field,
    get_field_attname,
    requires_update,
    update_object,
)

uu = lambda: str(uuid.uuid4())


def connection():
    conn = mysql.connector.connect(
        host=os.environ["MAGENTO_HOST"],
        port=os.environ["MAGENTO_PORT"],
        user=os.environ["MAGENTO_USR"],
        password=os.environ["MAGENTO_PW"],
        database=os.environ["MAGENTO_DB"],
    )
    return conn


def get_magento_orders(conn, order_date):
    db = conn.cursor()

    select_str = """
        SELECT e.item_id
        , e.order_id
        , e.sku
        , e.qty_ordered
        , e.price
        , o.status
        , cus.email
        , o.billing_address_id
        , o.shipping_address_id
        , o.grand_total
        , o.shipping_amount
        , o.subtotal
        , o.tax_amount
        , o.created_at
        , o.purchase_order_number
        , o.coupon_code
        , op.method
        , o.customer_note
        , o.increment_id 

        FROM sales_order_item AS e
        INNER JOIN sales_order AS o
        ON o.entity_id = e.order_id
        INNER JOIN sales_order_payment op
        ON op.parent_id = e.order_id
        INNER JOIN customer_entity AS cus
        ON cus.entity_id = o.customer_id
        WHERE o.customer_id IS NOT NULL
    """
    if order_date is not None:
        where_str = " AND (o.created_at >= '{}')".format(order_date)
    else:
        where_str = ""

    order_str = " ORDER BY e.order_id"
    query_str = select_str + where_str + order_str
    db.execute(query_str)
    result_orders = db.fetchall()

    address_where_str = """
        SELECT e.entity_id, e.customer_address_id, cus.firstname,
            cus.lastname, cus.street, cus.city, cus.postcode, e.postcode, e.street,
            e.city, e.telephone, e.firstname, e.lastname, cus_a.value, c.email
        FROM sales_order_address AS e
        LEFT JOIN customer_address_entity AS cus
        ON cus.entity_id = e.customer_address_id
        LEFT JOIN customer_entity AS c
        ON c.entity_id = cus.parent_id
        LEFT JOIN customer_address_entity_int AS cus_a
        ON cus_a.entity_id = e.customer_address_id
        LEFT JOIN eav_attribute AS eav 
        ON eav.attribute_id = cus_a.attribute_id 
        AND eav.attribute_code = 'odoo_address_id'
        WHERE e.parent_id IS NOT NULL
    """
    db.execute(address_where_str)
    result_address = {}
    for row_ad in db.fetchall():
        result_address[row_ad[0]] = row_ad
    conn.close()
    return {"order_items": result_orders, "order_address": result_address}


def get_customers(Model):
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        results = {str(item.email).lower(): item for item in queryset.all()}
    return results


def get_products(Model):
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        results = {str(item.sku).lower(): True for item in queryset.all()}
    return results


def get_customer_address(Model):
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        for item in queryset.select_related("customer").all():
            if item.customer is not None:
                pk = "%s_%s_%s_%s_%s_%s" % (
                    str(item.customer.email).strip(),
                    str(item.name).strip(),
                    str(item.street_address_1).strip(),
                    str(item.city).strip(),
                    str(item.type_address).strip(),
                    str(item.address_postal).strip(),
                )
                results[str(pk).lower()] = item

            if item.odoo_id > 0:
                results[item.odoo_id] = item
    return results


def parse_order(Model, item, customer):
    pk = uu()

    # check how the customer bit workz
    # add the id
    # mark as imported
    pp(item)

    if customer.get_group_code() == "TRADE":
        customer_type = "trade"
    else:
        customer_type = "retail"

    data = {
        get_field_attname(Model, "create_date"): item[13].strftime("%Y-%m-%d %H:%M:%S")
        + ".000000+00",
        get_field_attname(Model, "shipping_cost"): item[10],
        get_field_attname(Model, "subtotal"): item[11],
        get_field_attname(Model, "order_tax"): item[12],
        get_field_attname(Model, "order_total"): item[9],
        get_field_attname(Model, "status"): item[5] if item[5] == "canceled" else "order",
        get_field_attname(Model, "customer_id"): customer.id,
        get_field_attname(Model, "order_surcharge"): 0,
        get_field_attname(Model, "order_notes"): item[17],
        get_field_attname(Model, "purchase_order_ref"): item[14],
        get_field_attname(Model, "number"): item[18],
        get_field_attname(Model, "odoo_is_imported"): True,
    }

    if customer_type == "trade":
        data[get_field_attname(Model, "company_id")] = customer.company_id.uuid
        data[get_field_attname(Model, "payment_type")] = "credit"
    if customer_type == "retail":
        data[get_field_attname(Model, "company_id")] = None

        if item[16] == "braintree":
            data[get_field_attname(Model, "payment_type")] = "c_d_card"
        else:
            data[get_field_attname(Model, "payment_type")] = "d_d"

    data[Model._meta.pk.attname] = pk
    pp(data)
    return data


def parse_order_item(Model, item, order_uuid, sequence=0):
    pk = uu()
    data = {
        get_field_attname(Model, "product_price"): item[4],
        get_field_attname(Model, "product_quantity"): item[3],
        get_field_attname(Model, "product"): item[2],
        get_field_attname(Model, "order_uuid"): order_uuid,
        get_field_attname(Model, "sequence"): sequence,
    }
    data[Model._meta.pk.attname] = pk
    return Model(**data)


def parse_address(Model, cus_item, item, type_ads):
    pk = uu()
    data = {
        get_field_attname(Model, "name"): str(item[11]) + " " + str(item[12]),
        get_field_attname(Model, "street_address_1"): item[8],
        get_field_attname(Model, "city"): item[9],
        get_field_attname(Model, "type_address"): type_ads,
        get_field_attname(Model, "address_postal"): item[7],
        get_field_attname(Model, "customer"): cus_item.id,
    }
    if cus_item.get_group_code() == "TRADE":
        data[get_field_attname(Model, "company_id")] = cus_item.company_id.uuid
    else:
        data[get_field_attname(Model, "company_id")] = None
    data[Model._meta.pk.attname] = pk

    is_pass = check_length_fields(Model, data)
    if not is_pass:
        print("parse_address --- FIELD LENGTH TOO LONG - ", data)

    return data


def get_future_object_list(conn, order_date, Model, ModelProduct, ModelAddress):
    """User threadpool to get all data
    returns dicts"""
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_object_list = {
            executor.submit(get_customers, Model): "customers",
            executor.submit(get_products, ModelProduct): "products",
            executor.submit(get_customer_address, ModelAddress): "address",
            executor.submit(get_magento_orders, conn, order_date): "orders",
        }
        future_objects = as_completed(future_object_list)
        for future in future_objects:
            type_object = future_object_list[future]
            results[type_object] = future.result()
    return results


def execute():
    conn = connection()

    ModelProduct = _get_model("products.Product")
    ModelOrder = _get_model("products.order")
    ModelOrderItem = _get_model("products.orderitem")
    ModelCustomer = _get_model("customers.customuser")
    ModelAddress = _get_model("customers.addresses")

    order_date = os.environ["MAGENTO_ORDER_DATE"]
    results = get_future_object_list(conn, order_date, ModelCustomer, ModelProduct, ModelAddress)

    customers = results["customers"]
    products = results["products"]
    old_address = results["address"]  # django address, shouldn't need
    order_items = results["orders"]["order_items"]
    order_address = results["orders"]["order_address"]

    order_exists = {}
    orders_by_uuid = {}
    order_item_sequence = {}
    order_not_add = {}

    order_create_list = []
    order_item_create_list = []

    unique_orders = [y for _, y in {x[1]: x for x in order_items}.items()]

    for item in unique_orders:
        email = str(item[6]).lower()
        order_id = item[1]
        sku = str(item[2]).lower()
        # if the customer does not exists on the database django, This order will skip
        if not customers.get(email):
            print("This %s does not exists on the database django" % item[6])
            order_not_add[order_id] = item
            continue
        else:
            customer = customers[email]

        # create new order data
        if not order_exists.get(order_id):
            order_data = parse_order(ModelOrder, item, customer)
            pp(order_data)
            shipping_id = item[8]
            billing_id = item[7]

            add = order_address[shipping_id]
            bill = order_address[billing_id]
            add_dict = {
                "name": str(add[11]) + " " + str(add[12]),
                "street_address_1": add[8],
                "city": add[9],
                "address_postal": add[7],
            }
            shipping_address_str = ", ".join([y.replace("\n", "") for _, y in add_dict.items()])
            print(f" address for this order is {shipping_address_str}")
            bill_dict = {
                "name": str(add[11]) + " " + str(add[12]),
                "street_address_1": add[8],
                "city": add[9],
                "address_postal": add[7],
            }
            bill_address_str = ", ".join([y.replace("\n", "") for _, y in bill_dict.items()])
            print(f" address for this order is {bill_address_str}")

            order_data["address_shipping_str"] = shipping_address_str
            order_data["address_billing_str"] = bill_address_str

            order_exists[order_id] = {
                "pk": order_data[ModelOrder._meta.pk.attname],
                "order_data": ModelOrder(**order_data),
                "order_items": [],
                "item_sequence": 0,
            }
            order_obj = ModelOrder(**order_data)
            order_create_list.append(order_obj)
            orders_by_uuid[order_obj.uuid] = order_obj

    for item in order_items:
        # print(item)
        email = str(item[6]).lower()
        order_id = item[1]
        sku = str(item[2]).lower()

        # This order and order item will skip, so the product does not exists on the database django
        if order_not_add.get(order_id):
            continue

        # if the product does not exists on the database django, This order will skip
        if not products.get(sku):
            print("This %s - %s does not exists on the database django" % (item[6], item[2]))
            continue

        order_uuid = order_exists[order_id]["pk"]
        sequence = order_exists[order_id]["item_sequence"]

        order_item_data = parse_order_item(ModelOrderItem, item, order_uuid, sequence)
        order_exists[order_id]["order_items"].append(order_item_data)
        order_exists[order_id]["item_sequence"] += 1

        order_item_create_list.append(order_item_data)

    pp(order_exists)

    # Create items when does not exists on Django
    # bulk_create(
    # ModelAddress, in_add_object_list, len(in_add_object_list), "order address"
    # )
    bulk_create(
        ModelOrderItem,
        order_item_create_list,
        len(order_item_create_list),
        "order item",
    )
    bulk_create(ModelOrder, order_create_list, len(order_create_list), "order")

    ## link the above two, probably not most efficient
    all_order_items = ModelOrderItem.objects.all()
    all_order_items_dict = defaultdict(list)
    for ord_item in all_order_items:
        all_order_items_dict[ord_item.order_uuid].append(ord_item)

    all_orders = ModelOrder.objects.all()

    with transaction.atomic():
        for order in all_orders:
            order.items.set(all_order_items_dict[order.uuid])

    print(f"Orders of length {len(order_not_add.keys())} was not added")
