import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import DEFAULT_DB_ALIAS, models
from odoo.utils import (
    _get_model,
    bulk_create,
    bulk_delete,
    bulk_update,
    check_length_fields,
    get_field_attname,
    requires_update,
    update_object,
)

uu = lambda: str(uuid.uuid4())


def get_old_customers(Model):
    """SQL Query to get all customers
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        results = {str(item.email).lower().strip(): item for item in queryset.all()}
    return results


def get_old_companies(Model):
    """SQL Query to get all companies
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    results = {}
    if queryset.count() > 0:
        results = {str(item.company_code).lower(): item.uuid for item in queryset.all()}
    return results


def get_odoo_customers(conn):
    """SQL Query to get all customers
    from Odoo database, returns dicts"""

    cursor = conn.cursor(cursor_factory=DictCursor)
    query_str = """
        SELECT 
            e.user_name as email,
            e.web_password as password,
            SPLIT_PART(e.contact, ' ', 1) as first_name,
            SPLIT_PART(e.contact, ' ', 2) as last_name,
            e.id as odoo_id,
            res.ref as odoo_ref,
            res.name as res_name
        FROM webstore_details e
        INNER JOIN res_partner res
        on res.id = e.partner_id
        WHERE e.user_name IS NOT NULL
        AND e.create_date > (NOW() - Interval '5 Minutes')
    """
    cursor.execute(query_str)
    result = cursor.fetchall()
    cursor.close()
    return result


def parse_customer_data(Model, item):
    pk = uu()
    data = {
        "email": str(item["email"]).strip().lower(),
        get_field_attname(Model, "company_id"): item["company_id"],
        get_field_attname(Model, "group_id"): item["group_id"],
        "first_name": item["first_name"],
        "last_name": item["last_name"],
        "odoo_id": item["odoo_id"],
        "odoo_ref": item["odoo_ref"],
        "role": item["role"],
    }
    data[Model._meta.pk.attname] = pk
    return data


def execute():
    # Connect to ODOO Databases
    conn = Database.connect(settings.ODOO_DB_URI)
    Model = _get_model("customers.customuser")
    ModelComp = _get_model("customers.company")

    ModelGroup = _get_model("customers.groupextend")
    groups = (
        ModelGroup._default_manager.using(DEFAULT_DB_ALIAS).filter(group_code="TRADE").all()[:1]
    )
    trade_group = groups[0]

    """User threadpool to get all data"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_object_list = {
            executor.submit(get_old_customers, Model): "old_customers",
            executor.submit(get_old_companies, ModelComp): "old_companies",
            executor.submit(get_odoo_customers, conn): "odoo_customers",
        }
        future_objects = as_completed(future_object_list)
        for future in future_objects:
            type_object = future_object_list[future]
            if type_object == "old_customers":
                old_customers = future.result()
            if type_object == "old_companies":
                old_companies = future.result()
            if type_object == "odoo_customers":
                odoo_customers = future.result()

    in_object_list = []
    up_object_list = []
    exists_emails = {}
    for row in odoo_customers:
        item = dict(row)
        user_name = str(item["email"]).strip().lower()

        if user_name.find("@") == -1:
            # user_name = user_name + str(settings.EMAIL_NO_REPLY).lower()
            # item["email"] = item["email"] + settings.EMAIL_NO_REPLY
            continue

        if not exists_emails.get(user_name):
            exists_emails[user_name] = True
            odoo_ref = str(item["odoo_ref"]).lower()
            if not old_companies.get(odoo_ref):
                print("Need create company, with name is %s - %s" % (odoo_ref, item["res_name"]))
                continue

            comp_uuid = old_companies[odoo_ref]
            item["company_id"] = comp_uuid
            item["group_id"] = trade_group.id
            item["role"] = "admin"

            fields_map = {
                get_field_attname(Model, "company_id"): "company_id",
                get_field_attname(Model, "group_id"): "group_id",
                "first_name": "first_name",
                "last_name": "last_name",
                "odoo_id": "odoo_id",
                "odoo_ref": "odoo_ref",
            }
            model_rel_fields = {"company_id": "uuid", "group_id": "id"}
            odoo_data = parse_customer_data(Model, item)
            odoo_id = str(item["odoo_id"])
            if not old_customers.get(user_name):
                odoo_data["password"] = make_password(item["password"])
                print("Adding customer", odoo_data)
                in_object_list.append(Model(**odoo_data))
            else:
                pass
                # existing_obj = old_customers[user_name]
                # require_up = requires_update(Model, odoo_data, existing_obj, fields_map, model_rel_fields)
                # if require_up:
                #     print("Updating customer", odoo_data)
                #     for (field_name, field_value) in fields_map.items():
                #         field = Model._meta.get_field(field_value)
                #         if field.remote_field and isinstance(field.remote_field, models.ManyToOneRel):
                #             if odoo_data[field_name] is None:
                #                 setattr(existing_obj, field.attname, None)
                #             else:
                #                 setattr(
                #                     existing_obj,
                #                     field.attname,
                #                     odoo_data[field_name],
                #                 )
                #         else:
                #             setattr(existing_obj, field_value, odoo_data[field_name])
                #     up_object_list.append(existing_obj)

    bulk_create(Model, in_object_list, len(in_object_list), "customer")
    # bulk_update(Model, up_object_list, fields_map.keys(), len(up_object_list), "customer")
