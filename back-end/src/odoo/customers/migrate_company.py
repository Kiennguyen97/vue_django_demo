import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.apps import apps
from django.conf import settings
from django.core.serializers import base
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError
from django.utils.text import slugify
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


def get_django_companies(Model):
    """SQL Query to get all companies
    from Django database, returns dicts"""
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        for item in queryset.all():
            results[str(item.company_code).strip()] = item
            results[item.uuid] = item
    return results


def get_address(Model):
    """SQL Query to get all address link with odoo
    from Django database, returns dicts"""
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).filter(odoo_id__gt=0)
    results = {}
    if queryset.count() > 0:
        results = {str(x.odoo_id): x for x in queryset.select_related("company_id").all()}
    return results


def get_django_pl_rel(Model):
    """SQL Query to get all price list and cpgs
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    ids = []
    if queryset.count() > 0:
        for item in queryset.select_related("company", "pricelist").all():
            ref = str(item.company.company_code)
            pk = "%s_%s" % (ref, item.pricelist.uuid)
            ids.append(item.id)
            results[pk] = item.id
    results["ids"] = ids
    return results


def get_django_cpg_rel(Model):
    """SQL Query to get all price list and cpgs
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    ids = []
    if queryset.count() > 0:
        for item in queryset.select_related("closed_purchase_group", "company").all():
            ref = str(item.company.company_code)
            pk = "%s_%s" % (ref, item.closed_purchase_group.uuid)
            ids.append(item.id)
            results[pk] = item.id
    results["ids"] = ids
    return results


def get_django_pl_and_cpg_rel(ModelRel, ModelCpgRel):
    return {
        "pl_rel": get_django_pl_rel(ModelRel),
        "cpg_rel": get_django_cpg_rel(ModelCpgRel),
    }


def get_django_product_pl_cpg(Model):
    """SQL Query to get all price list and cpgs
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        results = {str(x.odoo_id): x.uuid for x in queryset.all()}
    return results


def get_django_pl_and_cpg(Model, ModelCpg):
    pl = get_django_product_pl_cpg(Model)
    cpgs = get_django_product_pl_cpg(ModelCpg)
    return {"pl": pl, "cpgs": cpgs}


def get_odoo_pl_cpg_companies_address(conn):
    """SQL Query to get all pricelist, cpgs, address & companies
    from Odoo database, returns dicts"""

    cursor = conn.cursor(cursor_factory=DictCursor)
    # get all companies
    query_str = """SELECT
        TRIM(e.ref) as ref
        , e.id
        , e.name
        , e.phone
        , e.no_admin_fee
        , t1.name as sales_name
        , t1.email as sales_email
        FROM res_partner e
        LEFT JOIN (
            SELECT res_u.id, res_p.name, res_p.email
            FROM res_users res_u
            INNER JOIN res_partner res_p 
            ON res_p.id = res_u.partner_id
        ) t1 ON t1.id = e.sales_executive
        WHERE e.ref IS NOT NULL
            AND e.customer=True
            AND e.type='contact'
            AND e.is_company=True
            AND e.active=True
    """
    cursor.execute(query_str)

    result_com = [dict(x) for x in cursor.fetchall()]
    list_company_ids = tuple([x["id"] for x in result_com])

    address_query_str = """SELECT a.id
        , TRIM(a.name) as name
        , TRIM(a.street) as street
        , a.type
        , TRIM(b.name) as parent_name
        , TRIM(a.street2) as street2
        , TRIM(a.city) as city
        , TRIM(b.ref) as ref
        , a.email
        , a.zip
        , a.phone
        FROM res_partner a
        INNER JOIN res_partner b on a.parent_id = b.id
        WHERE a.type IN ('delivery', 'invoice')
            AND a.active=True
            AND a.parent_id in %(company_ids)s
        ;"""

    cursor.execute(address_query_str, {"company_ids": list_company_ids})
    result_add = cursor.fetchall()

    ### creates a dict with keys of odoo code, vals is list(addresses)
    # for x in cursor.fetchall():
    #     item = dict(x)
    #     if not result_add.get(item["ref"]):
    #         rows = []
    #     else:
    #         rows = result_add[item["ref"]]
    #     rows.append(item)
    #     result_add[item["ref"]] = rows

    # get all pricelist
    pl_query_str = """
        SELECT TRIM(res.ref) as ref,
            cast(substr(e.value_reference, 19) as integer) as pricelist_id
        FROM ir_property e
        INNER JOIN res_partner res
        ON res.id = cast(substr(e.res_id, 13) as integer)
        WHERE e.name = 'property_product_pricelist'
        AND res.id in %(company_ids)s;
    """
    cursor.execute(pl_query_str, {"company_ids": list_company_ids})
    result_pl = cursor.fetchall()

    # get all CPG
    cpg_query_str = """
        SELECT TRIM(res.ref) as ref
        , e.product_pricelist_id pricelist_id
        FROM product_pricelist_res_partner_rel e
        INNER JOIN res_partner res
        ON res.id = e.res_partner_id
        WHERE res.id in %(company_ids)s
        GROUP BY TRIM(res.ref)
        , e.product_pricelist_id 
    """
    cursor.execute(cpg_query_str, {"company_ids": list_company_ids})
    result_cpg = cursor.fetchall()

    cursor.close()
    return {
        "items": result_com,
        "address_items": result_add,
        "pl": result_pl,
        "cpg": result_cpg,
    }


def get_future_object_list(conn, Model, AddressModel, ModelPl, ModelCpg, ModelPlRel, ModelCpgRel):
    """User threadpool to get all data
    returns dicts"""
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_object_list = {
            executor.submit(get_django_companies, Model): "django",
            executor.submit(get_odoo_pl_cpg_companies_address, conn): "odoo",
            executor.submit(get_address, AddressModel): "django_address",
            executor.submit(
                get_django_pl_and_cpg_rel, ModelPlRel, ModelCpgRel
            ): "django_pl_cpg_rel",
            executor.submit(get_django_pl_and_cpg, ModelPl, ModelCpg): "django_pl_cpg",
        }
        future_objects = as_completed(future_object_list)
        for future in future_objects:
            type_object = future_object_list[future]
            results[type_object] = future.result()
    return results


def parse_company_data(Model, item):
    pk = uu()

    if item["sales_name"] in (None, "Unassigned"):
        item["sales_name"] = settings.DEFAULT_SALES_PERSON["name"]
        item["sales_email"] = settings.DEFAULT_SALES_PERSON["email"]

    data = {
        "name": item["name"],
        "company_code": str(item["ref"]).strip(),
        "phone_number": item["phone"] if item["phone"] else "",
        "no_admin_fee": True if item["no_admin_fee"] else False,
        "sales_name": item["sales_name"],
        "sales_email": item["sales_email"],
    }
    data[Model._meta.pk.attname] = pk
    return data


def parse_address_data(Model, item):
    pk = uu()
    data = {
        "name": item["name"] if item["name"] else item["parent_name"],
        "street_address_1": item["street"] if item["street"] else "",
        "street_address_2": item["street2"] if item["street2"] else "",
        "city": item["city"] if item["city"] else "",
        "type_address": "SHIP" if (item["type"] == "delivery") else "BILL",
        "phone": item["phone"] if item["phone"] else "",
        "address_postal": item["zip"] if item["zip"] else "",
        "odoo_id": item["id"],
    }
    data[Model._meta.pk.attname] = pk
    return data


def parse_pl_cpg_company_rel_data(Model, item):
    data = {}
    for field_name, field_value in item.items():
        field = Model._meta.get_field(field_name)
        data[field.attname] = field_value
    return Model(**data)


def get_company_fields_map():
    ## maps fields from odoo to django names
    ## fields_map and parse_company_data are possibly redundant
    fields_map = {
        "name": "name",
        "phone_number": "phone_number",
        "no_admin_fee": "no_admin_fee",
        "sales_name": "sales_name",
        "sales_email": "sales_email",
    }
    return fields_map


def get_address_fields_map(company_id_field):
    ## maps fields from odoo to django names
    ## fields_map and parse_company_data are possibly redundant
    fields_map = {
        "name": "name",
        "street_address_1": "street_address_1",
        "street_address_2": "street_address_2",
        "city": "city",
        "phone": "phone",
        "type_address": "type_address",
        "address_postal": "address_postal",
        company_id_field.attname: "company_id",
    }
    return fields_map


def sync_company(Model, odoo_results, old_object, fields_map, ERRORS=[]):
    # process for company
    in_object_list = []
    up_object_list = []
    add_i = 0
    up_i = 0
    pks = {}
    for row in odoo_results["items"]:
        item = dict(row)
        ref = str(item["ref"]).strip()
        odoo_data = parse_company_data(Model, item)
        is_pass = check_length_fields(Model, odoo_data)
        if not is_pass:
            ERRORS.append("FIELD LENGTH TOO LONG - " + json.dumps(odoo_data))
            print("FIELD LENGTH TOO LONG - ", odoo_data)
            continue

        # if not there, append to the insert list

        if not old_object.get(ref):
            in_object_list.append(Model(**odoo_data))
            print("Adding Item", odoo_data)
            add_i += 1
            pks[ref] = odoo_data[Model._meta.pk.attname]

        # otherwise, check if update needed
        else:
            existing_obj = old_object[ref]
            pks[ref] = existing_obj.uuid
            require_up = requires_update(Model, odoo_data, existing_obj, fields_map, {})
            if require_up:
                print("Updating Item", odoo_data)
                obj = update_object(Model, odoo_data, existing_obj, fields_map)
                up_object_list.append(obj)
                up_i += 1
    return {
        "in_object_list": in_object_list,
        "up_object_list": up_object_list,
        "pks": pks,
        "add_i": add_i,
        "up_i": up_i,
    }


def sync_address(
    Model,
    odoo_results,  # list of dicts with data (address_items)
    old_object,  # django addresses with {odoo_id: address_obj}
    pks,  # {odoo code : pk} map
    fields_map,
    model_rels,  # map of {'odoocode': obj, 'company_uuid': obj}
    ERRORS=[],
):
    in_object_list = []
    up_object_list = []
    del_ids = []
    add_i = 0
    up_i = 0

    company_id_field = Model._meta.get_field("company_id")

    odoo_address_ids = set([x["id"] for x in odoo_results["address_items"]])
    django_address_ids = set([int(x) for x in old_object.keys()])
    del_ids = django_address_ids - odoo_address_ids

    for row in odoo_results["address_items"]:
        item = dict(row)
        ref = str(item["ref"])
        odoo_data = parse_address_data(Model, item)
        odoo_data[company_id_field.attname] = pks[ref]
        is_pass = check_length_fields(Model, odoo_data)

        if not is_pass:
            ERRORS.append("FIELD LENGTH TOO LONG - " + json.dumps(odoo_data))
            print("FIELD LENGTH TOO LONG - ", odoo_data)
            continue

        odoo_id = str(odoo_data["odoo_id"])

        if not old_object.get(odoo_id):
            print("Adding Item", odoo_data)
            in_object_list.append(Model(**odoo_data))
            add_i += 1
        else:
            existing_obj = old_object[odoo_id]
            require_up = requires_update(
                Model, odoo_data, existing_obj, fields_map, {"company_id": "uuid"}
            )
            if require_up:
                print("Updating Item", odoo_data)
                odoo_data[Model._meta.pk.attname] = existing_obj.uuid
                up_object_list.append(Model(**odoo_data))
                up_i += 1
    return {
        "in_object_list": in_object_list,
        "up_object_list": up_object_list,
        "del_ids": del_ids,
        "add_i": add_i,
        "up_i": up_i,
    }


def sync_pricelist_link_company(
    Model,
    odoo_results,  # {'ref': '5doc', 'pricelist_id': 1}
    old_object,  # {'ids': []}
    pks,  # {'5doc': 'uuid'}
    old_parent_obj,  # {}
    old_ids,  # []
):
    # process for pricelist link with company
    in_object_list = []
    add_i = 0
    for row in odoo_results["pl"]:
        item = dict(row)
        ref = str(item["ref"]).strip()
        pl_id = str(item["pricelist_id"])

        # if company not exist or pricelist not exist in django
        if not pks.get(ref) or not old_parent_obj.get(pl_id):
            continue

        odoo_data = {"company": pks[ref], "pricelist": old_parent_obj[pl_id]}
        pk = "%s_%s" % (ref, old_parent_obj[pl_id])
        if not old_object.get(pk):
            print(f"need to add, {pk}")
            in_object_list.append(parse_pl_cpg_company_rel_data(Model, odoo_data))
            add_i += 1
        else:
            old_ids.remove(old_object[pk])

    return {
        "in_object_list": in_object_list,
        "del_ids": old_ids,
        "add_i": add_i,
    }


def sync_cpg_link_cpmpany(Model, odoo_results, old_object, pks, old_parent_obj, old_ids):
    # process for cpg link with company
    in_object_list = []
    add_i = 0
    for row in odoo_results["cpg"]:
        item = dict(row)
        # if row['ref'] == 'ZZZ9816':
        #     import pdb; pdb.set_trace()
        ref = str(item["ref"]).strip()
        pl_id = str(item["pricelist_id"])
        if not pks.get(ref) or not old_parent_obj.get(pl_id):
            continue

        odoo_data = {
            "company": pks[ref],
            "closed_purchase_group": old_parent_obj[pl_id],
        }
        pk = "%s_%s" % (ref, old_parent_obj[pl_id])
        if not old_object.get(pk):
            print(f"need to add CPG, {pk}")
            in_object_list.append(parse_pl_cpg_company_rel_data(Model, odoo_data))
            add_i += 1
        else:
            old_ids.remove(old_object[pk])

    print(f"going to remove {old_ids}")
    return {
        "in_object_list": in_object_list,
        "del_ids": old_ids,
        "add_i": add_i,
    }


def execute():
    """Main Function"""
    # Connect to ODOO Databases
    conn = Database.connect(settings.ODOO_DB_URI)
    ERRORS = []  ## wlil use this to email admin with errors
    Model = _get_model("customers.company")
    AddressModel = _get_model("customers.addresses")
    company_id_field = AddressModel._meta.get_field("company_id")
    ModelPl = _get_model("products.pricelist")
    ModelCpg = _get_model("products.closedpurchasegroup")
    ModelPlRel = _get_model("products.pricelistcustomerrel")
    ModelCpgRel = _get_model("products.closedpurchasegrouprel")

    # get all data
    results = get_future_object_list(
        conn, Model, AddressModel, ModelPl, ModelCpg, ModelPlRel, ModelCpgRel
    )

    # get all from ODOO Database
    odoo_results = results["odoo"]
    # get all companies from Django
    django_companies = results["django"]
    # get all address from Django
    django_address = results["django_address"]

    # get all pl & cpg link witn company from Django
    old_pl_cpg_rel = results["django_pl_cpg_rel"]
    old_pl_rel = old_pl_cpg_rel["pl_rel"]
    old_cpg_rel = old_pl_cpg_rel["cpg_rel"]
    old_pl_rel_ids = old_pl_rel["ids"]
    old_cpg_rel_ids = old_cpg_rel["ids"]

    # get all pl & cpg from Django
    old_pl_cpg = results["django_pl_cpg"]
    old_pl = old_pl_cpg["pl"]
    old_cpg = old_pl_cpg["cpgs"]

    fields_map = get_company_fields_map()

    add_fields_map = get_address_fields_map(company_id_field)
    model_rels = {"company_id": django_companies}

    company_result = sync_company(Model, odoo_results, django_companies, fields_map, ERRORS)
    pks = company_result["pks"]
    add_result = sync_address(
        AddressModel,
        odoo_results,
        django_address,
        pks,
        add_fields_map,
        model_rels,
        ERRORS,
    )
    pl_rel_result = sync_pricelist_link_company(
        ModelPlRel, odoo_results, old_pl_rel, pks, old_pl, old_pl_rel_ids
    )
    cpg_rel_result = sync_cpg_link_cpmpany(
        ModelCpgRel, odoo_results, old_cpg_rel, pks, old_cpg, old_cpg_rel_ids
    )

    # Delete items when does not exists on Odoo
    bulk_delete(AddressModel, "odoo_id", add_result["del_ids"])
    bulk_delete(ModelPlRel, "id", pl_rel_result["del_ids"])
    bulk_delete(ModelCpgRel, "id", cpg_rel_result["del_ids"])

    # Create items when does not exists on Django
    bulk_create(Model, company_result["in_object_list"], company_result["add_i"], "companie")
    bulk_create(AddressModel, add_result["in_object_list"], add_result["add_i"], "address")
    bulk_create(
        ModelPlRel,
        pl_rel_result["in_object_list"],
        pl_rel_result["add_i"],
        "pricelist link with companie",
    )
    bulk_create(
        ModelCpgRel,
        cpg_rel_result["in_object_list"],
        cpg_rel_result["add_i"],
        "cpg link with companie",
    )

    # Update items when compare values is difference between Django and Odoo
    bulk_update(
        Model,
        company_result["up_object_list"],
        fields_map.values(),
        company_result["up_i"],
        "companie",
    )
    bulk_update(
        AddressModel,
        add_result["up_object_list"],
        add_fields_map.keys(),
        add_result["up_i"],
        "address",
    )
