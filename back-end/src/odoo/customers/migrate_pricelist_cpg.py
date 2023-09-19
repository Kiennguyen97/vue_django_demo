import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models.expressions import Q
from odoo.utils import (
    _get_model,
    bulk_create,
    bulk_delete,
    bulk_update,
    check_length_fields,
    requires_update,
    update_object,
)

uu = lambda: str(uuid.uuid4())


def get_django_product_pl_cpg(Model):
    """SQL Query to get all price list and cpgs
    from Django database, returns dict like
    {'odoo_id': obj, 'uuid': obj, 'odoo_ids': [1,2,3]}
    """
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    items = []
    if queryset.count() > 0:
        for item in queryset.all():
            results[str(item.odoo_id)] = item
            results[item.uuid] = item
            items.append(item.odoo_id)
    results["odoo_ids"] = items
    return results


def get_django_pl_and_cpgs(Model, ModelCpg):
    """Gets existing pricelists & cpgs from django"""
    pl = get_django_product_pl_cpg(Model)
    cpgs = get_django_product_pl_cpg(ModelCpg)
    return {"pl": pl, "cpgs": cpgs}


def get_django_pl_items(Model):
    """SQL Query to get all price list items
    from Django database, returns dicts"""
    table_name = Model._meta.db_table
    obj = Model._default_manager
    raw_query = "SELECT * FROM %s" % table_name
    results = {}
    items = []
    for item in obj.raw(raw_query, using=DEFAULT_DB_ALIAS):
        pk = "%s_%s" % (item.pricelist_id, str(item.product_id))
        results[pk] = item
        items.append(item.id)
    results["ids"] = items
    return results


def get_django_cpg_items(Model):
    """SQL Query to get all cpg items
    from Django database, returns dicts"""

    table_name = Model._meta.db_table
    obj = Model._default_manager
    raw_query = "SELECT * FROM %s" % table_name
    results = {}
    items = []
    for item in obj.raw(raw_query, using=DEFAULT_DB_ALIAS):
        pk = "%s_%s" % (item.closed_purchase_group_id, str(item.product_id))
        results[pk] = item
        items.append(item.id)
    results["ids"] = items
    return results


def get_django_pl_cpg_items(Model, ModelCpgItem):
    """Gets existing pl items and cpg items from django"""
    pl_items = get_django_pl_items(Model)
    cpg_items = get_django_cpg_items(ModelCpgItem)
    return {"pl_items": pl_items, "cpg_items": cpg_items}


def get_django_products(Model):
    """SQL Query to get all products
    from Django database, returns dicts"""
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        results = {str(x.sku): x for x in queryset.all()}
    return results


def get_odoo_cpgs(conn):
    """SQL Query to get all price list
    from Odoo database, returns dicts"""
    cursor = conn.cursor(cursor_factory=DictCursor)
    cpg_query_str = """
        SELECT
        a.id
        , a.name
        , a.close_purchase_order::BOOL
        FROM product_pricelist a
        WHERE a.active=True
        AND a.close_purchase_order=True
    """
    cursor.execute(cpg_query_str)
    results = [dict(x) for x in cursor.fetchall()]
    cpg_item_query_str = """
        SELECT
        a.pricelist_id
        , pt.default_code AS sku
        FROM product_pricelist_item a
        INNER JOIN product_pricelist b ON b.id = a.pricelist_id
        INNER JOIN product_template pt ON a.product_tmpl_id = pt.id
        WHERE b.active=True 
            AND pt.default_code is not null
            AND b.close_purchase_order = True
        GROUP BY (a.pricelist_id, pt.default_code)
        ;
    """
    cursor.execute(cpg_item_query_str)
    cpg_items = [dict(x) for x in cursor.fetchall()]
    cursor.close()
    return {"cpg": results, "cpg_items": cpg_items}


def get_odoo_pricelists(conn):
    """SQL Query to get all price list
    from Odoo database, returns dicts"""
    cursor = conn.cursor(cursor_factory=DictCursor)
    query_str = """
        SELECT
        a.id
        , a.name
        , a.close_purchase_order::BOOL
        FROM product_pricelist a
        WHERE a.active=True
        AND a.close_purchase_order != True
        -- must use != true, sometimes it can be null/False
        ;
    """
    cursor.execute(query_str)
    results = [dict(x) for x in cursor.fetchall()]
    pl_query_str = """
        SELECT
        a.pricelist_id
        , pt.default_code AS sku
        , min(a.fixed_price) AS price
        FROM product_pricelist_item a
        INNER JOIN product_pricelist b ON b.id = a.pricelist_id
        INNER JOIN product_template pt ON a.product_tmpl_id = pt.id
        WHERE b.active=True 
            AND b.close_purchase_order != True
            AND a.fixed_price > 0
            AND pt.default_code is not null
        GROUP BY (a.pricelist_id, pt.default_code)
    """
    cursor.execute(pl_query_str)
    pl_items = [dict(x) for x in cursor.fetchall()]
    cursor.close()
    return {"pl": results, "pl_items": pl_items}


def get_future_object_list(conn, Model, ModelCpg, ModelItem, ModelCpgItem, ModelProduct):
    """User threadpool to get all data
    returns dicts"""
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_object_list = {
            executor.submit(get_django_pl_and_cpgs, Model, ModelCpg): "django_pl_cpg",
            executor.submit(get_django_products, ModelProduct): "django_products",
            executor.submit(
                get_django_pl_cpg_items, ModelItem, ModelCpgItem
            ): "django_pl_cpg_items",
            executor.submit(get_odoo_pricelists, conn): "odoo_pl",
            executor.submit(get_odoo_cpgs, conn): "odoo_cpg",
        }
        future_objects = as_completed(future_object_list)
        for future in future_objects:
            type_object = future_object_list[future]
            results[type_object] = future.result()
    return results


def parse_pricelist_and_cpg_data(Model, item):
    pk = uu()
    data = {
        "name": item["name"],
        "odoo_id": item["id"],
    }
    data[Model._meta.pk.attname] = pk
    return data


def parse_item_data(Model, item):
    data = {}
    for field_name, field_value in item.items():
        field = Model._meta.get_field(field_name)
        data[field.attname] = field_value
    return Model(**data)


def execute():
    # Connect to ODOO Databases
    conn = Database.connect(settings.ODOO_DB_URI)
    ModelPricelist = _get_model("products.pricelist")
    ModelPricelistItem = _get_model("products.pricelistitem")
    ModelCpg = _get_model("products.closedpurchasegroup")
    ModelCpgItem = _get_model("products.closedpurchasegroupitem")
    ModelProduct = _get_model("products.product")
    ERRORS = []  ## wlil use this to email admin with errors
    # get all data
    results = get_future_object_list(
        conn, ModelPricelist, ModelCpg, ModelPricelistItem, ModelCpgItem, ModelProduct
    )

    old_pricelist = results["django_pl_cpg"]["pl"]
    old_cpgs = results["django_pl_cpg"]["cpgs"]

    old_pl_items = results["django_pl_cpg_items"]["pl_items"]
    old_cpgs_items = results["django_pl_cpg_items"]["cpg_items"]

    django_products = results["django_products"]

    ## list of ids that are in django, pricelist, cpgs, items for both
    django_pl_odoo_ids = old_pricelist["odoo_ids"]
    django_cpg_odoo_ids = old_cpgs["odoo_ids"]
    django_pl_it_ids = old_pl_items["ids"]
    django_cpg_it_ids = old_cpgs_items["ids"]

    odoo_pricelists = results["odoo_pl"]["pl"]
    odoo_pricelist_items = results["odoo_pl"]["pl_items"]

    odoo_cpgs = results["odoo_cpg"]["cpg"]
    odoo_cpg_items = results["odoo_cpg"]["cpg_items"]

    odoo_pricelist_and_cpg = odoo_pricelists + odoo_cpgs
    odoo_pricelist_and_cpg_items = odoo_pricelist_items + odoo_cpg_items

    insert_pl_object_list = []
    insert_cpgs_object_list = []
    up_pl_object_list = []
    up_pl_item_object_list = []
    up_cpgs_object_list = []
    insert_pl_item_object_list = []
    insert_cpg_item_object_list = []
    pl_add_i = 0
    cpg_add_i = 0
    pl_up_i = 0
    cpg_up_i = 0
    pl_it_add_i = 0
    pl_it_up_i = 0
    cpg_it_add_i = 0

    fields_map = {
        "name": "name",
    }

    pl_pks = {}
    cpg_pks = {}

    existing_pl_items_ids = []

    for item_data in odoo_pricelist_and_cpg:
        odoo_id = str(item_data["id"])

        ## run on the closed purchase order
        if item_data["close_purchase_order"] == True:
            odoo_data = parse_pricelist_and_cpg_data(ModelCpg, item_data)
            if not old_cpgs.get(odoo_id):
                print("Adding Item", odoo_data)
                insert_cpgs_object_list.append(ModelCpg(**odoo_data))
                cpg_pks[odoo_id] = odoo_data[ModelCpg._meta.pk.attname]
                cpg_add_i += 1
            else:
                existing_obj = old_cpgs[odoo_id]
                django_cpg_odoo_ids.remove(item_data["id"])
                cpg_pks[odoo_id] = existing_obj.uuid
                require_up = requires_update(ModelCpg, odoo_data, existing_obj, fields_map)
                if require_up:
                    print("Updating Item", odoo_data)
                    obj = update_object(ModelCpg, odoo_data, existing_obj, fields_map)
                    up_cpgs_object_list.append(obj)
                    cpg_up_i += 1

        else:  ## run on pricelists
            odoo_data = parse_pricelist_and_cpg_data(ModelPricelist, item_data)
            if not old_pricelist.get(odoo_id):
                print("Adding Item", odoo_data)
                insert_pl_object_list.append(ModelPricelist(**odoo_data))
                pl_pks[odoo_id] = odoo_data[ModelPricelist._meta.pk.attname]
                pl_add_i += 1
            else:
                existing_obj = old_pricelist[odoo_id]
                django_pl_odoo_ids.remove(item_data["id"])
                pl_pks[odoo_id] = existing_obj.uuid
                require_up = requires_update(ModelPricelist, odoo_data, existing_obj, fields_map)
                if require_up:
                    print("Updating Item", odoo_data)
                    obj = update_object(ModelPricelist, odoo_data, existing_obj, fields_map)
                    up_pl_object_list.append(obj)
                    pl_up_i += 1

    for item_data in odoo_pricelist_and_cpg_items:
        odoo_id = str(item_data["pricelist_id"])
        sku = str(item_data["sku"])
        if not django_products.get(sku):
            continue

        ## if the parent is in the pricelist, process it as a
        ## pricelist item
        if pl_pks.get(odoo_id):
            odoo_item_data = {
                "pricelist": pl_pks[odoo_id],
                "product": item_data["sku"],
                "price": item_data["price"],
            }
            pk = "%s_%s" % (pl_pks[odoo_id], sku)
            if not old_pl_items.get(pk):
                print("Adding Item", odoo_item_data)
                insert_pl_item_object_list.append(
                    parse_item_data(ModelPricelistItem, odoo_item_data)
                )
                pl_it_add_i += 1
            else:
                existing_obj = old_pl_items[pk]
                existing_pl_items_ids.append(existing_obj.id)
                # django_pl_it_ids.remove(existing_obj.id)
                require_up = requires_update(
                    ModelPricelistItem, odoo_item_data, existing_obj, {"price": "price"}
                )
                if require_up:
                    print("Updating Item", odoo_item_data)
                    obj = update_object(
                        ModelPricelistItem,
                        odoo_item_data,
                        existing_obj,
                        {"price": "price"},
                    )
                    up_pl_item_object_list.append(obj)
                    pl_it_up_i += 1

        ## if the parent is in the cpg, process it as a cpg item
        elif cpg_pks.get(odoo_id):
            odoo_item_data = {
                "closed_purchase_group": cpg_pks[odoo_id],
                "product": item_data["sku"],
            }
            pk = "%s_%s" % (cpg_pks[odoo_id], sku)
            if not old_cpgs_items.get(pk):
                print("Adding Item", odoo_item_data)
                insert_cpg_item_object_list.append(parse_item_data(ModelCpgItem, odoo_item_data))
                cpg_it_add_i += 1
            else:
                existing_obj = old_cpgs_items[pk]
                django_cpg_it_ids.remove(existing_obj.id)
        else:
            pass

    # get the items of price list will remove
    delete_pl_item_ids = set(django_pl_it_ids) - set(existing_pl_items_ids)

    # Delete items when does not exists on Odoo
    # these lists are generated by a complete list of django ids at the start,
    # then as the odoo ids are looped through, the django ones are removed
    # hence, any left in the list were not in Odoo and should be removed.
    # bulk_delete(ModelPricelistItem, "id", django_pl_it_ids)
    bulk_delete(ModelPricelistItem, "id", delete_pl_item_ids)
    bulk_delete(ModelCpgItem, "id", django_cpg_it_ids)
    bulk_delete(ModelPricelist, "odoo_id", django_pl_odoo_ids)
    bulk_delete(ModelCpg, "odoo_id", django_cpg_odoo_ids)

    # Create items when does not exists on Django
    bulk_create(ModelPricelist, insert_pl_object_list, pl_add_i, "price list")
    bulk_create(ModelCpg, insert_cpgs_object_list, cpg_add_i, "CPG")
    bulk_create(ModelPricelistItem, insert_pl_item_object_list, pl_it_add_i, "price list item")
    bulk_create(ModelCpgItem, insert_cpg_item_object_list, cpg_it_add_i, "CPG item")

    # Update items when compare values is difference between Django and Odoo
    bulk_update(ModelCpg, up_cpgs_object_list, fields_map.values(), cpg_up_i, "CPG")
    bulk_update(ModelPricelist, up_pl_object_list, fields_map.values(), pl_up_i, "price list")
    bulk_update(
        ModelPricelistItem,
        up_pl_item_object_list,
        ["price"],
        pl_it_up_i,
        "price list item",
    )
