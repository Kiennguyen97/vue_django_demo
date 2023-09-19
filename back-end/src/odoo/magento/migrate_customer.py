import json
import os
import sys
import uuid

import mysql.connector

from django.apps import apps
from django.core.serializers import base
from django.core.serializers.base import DeserializationError
from django.db import DEFAULT_DB_ALIAS
from odoo.utils import _get_model, bulk_create, get_field_attname

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


def get_company():
    Model = _get_model("customers.company")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    if queryset.order_by().count() > 0:
        for item in queryset.all():
            items[item.company_code.lower()] = item
    return items


def get_django_customer():
    Model = _get_model("customers.customuser")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    if queryset.order_by().count() > 0:
        for item in queryset.all():
            items[item.email.lower()] = item
    return items


def get_django_group():
    Model = _get_model("customers.groupextend")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    if queryset.order_by().count() > 0:
        for item in queryset:
            items[item.group_code.lower()] = item
    return items


def get_customer():
    conn = connection()
    db = conn.cursor()
    where_str = ""
    join_str = ""
    select_str = "entity_id, email, firstname, lastname, password_hash, default_billing, default_shipping, taxvat, created_at"

    db.execute("SELECT %s FROM customer_entity AS e %s %s" % (select_str, join_str, where_str))
    customers = db.fetchall()
    conn.close()
    return customers


def get_attribute_odoo():
    conn = connection()
    db = conn.cursor()
    join_str = "INNER JOIN eav_attribute AS eav ON eav.attribute_id = e.attribute_id"
    query_str = (
        "SELECT entity_id, value FROM customer_entity_int AS e %s WHERE eav.attribute_code = 'odoo_id'"
        % join_str
    )
    db.execute(query_str)
    data = db.fetchall()
    conn.close()
    items = {}
    for row in data:
        items[row[0]] = row[1]
    return items


def get_email_override_attribute():
    conn = connection()
    db = conn.cursor()
    join_str = "INNER JOIN eav_attribute AS eav ON eav.attribute_id = e.attribute_id"
    query_str = (
        "SELECT entity_id, value FROM customer_entity_varchar AS e %s WHERE eav.attribute_code = 'email_override'"
        % join_str
    )
    db.execute(query_str)
    data = db.fetchall()
    conn.close()
    items = {}
    for row in data:
        items[row[0]] = row[1]
    return items


def get_customer_address():
    conn = connection()
    db = conn.cursor()
    query_str = "SELECT entity_id, parent_id, firstname, lastname, street, city, postcode FROM customer_address_entity AS e"
    db.execute(query_str)
    address = db.fetchall()
    conn.close()
    return address


def parse_customer_address(Model, cus_item, item, type_ads):
    pk = uu()
    street_add = item[4].split("\n")
    street_add_1 = street_add[0]
    street_add_2 = ", ".join(street_add[1:])
    data = {
        "name": item[2] + " " + item[3],
        "street_address_1": street_add_1,
        "street_address_2": street_add_2,
        "city": item[5],
        "type_address": type_ads,
        "address_postal": item[6],
        "company_id": cus_item["company_id"],
    }
    data[get_field_attname(Model, "customer")] = cus_item["pk"]
    data[Model._meta.pk.attname] = pk
    return data


def execute():
    address = get_customer_address()
    odoo_ids = get_attribute_odoo()
    customers = get_customer()
    companies = get_company()
    django_customers = get_django_customer()
    django_group = get_django_group()
    email_overrides = get_email_override_attribute()
    cus_exists_items = {}
    cus_pks = {}
    ModelCustomer = _get_model("customers.customuser")
    customer_object_list = []
    cus_add_i = 0
    for customer in customers:
        email = str(customer[1]).strip().lower()
        if django_customers.get(email):
            continue
        customer_id = customer[0]
        pk = uu()
        cus_data = {
            "first_name": customer[2],
            "last_name": customer[3],
            "email": email,
            "password_hash": customer[4],
            "date_joined": customer[8].strftime("%Y-%m-%d %H:%M:%S") + ".000000+00",
            "odoo_id": 0,
            "odoo_ref": "",
        }
        if not odoo_ids.get(customer_id):
            cus_data["group_id"] = django_group["retail"]
            cus_data["company_id"] = None
            cus_pks[customer_id] = {
                "pk": pk,
                "default_billing": customer[5],
                "default_shipping": customer[6],
                "company_id": cus_data["company_id"],
                "email": cus_data["email"],
            }
        else:
            odoo_id = odoo_ids[customer_id]
            cus_data["odoo_id"] = odoo_id
            if customer[7] is not None:
                cus_data["odoo_ref"] = customer[7]
                if not companies.get(customer[7].lower()):
                    cus_data["company_id"] = None
                    cus_data["group_id"] = django_group["retail"]
                else:
                    company_id = companies[customer[7].lower()]
                    cus_data["company_id"] = company_id
                    cus_data["group_id"] = django_group["trade"]

        if not email_overrides.get(customer_id):
            cus_data["email_override"] = ""
        else:
            cus_data["email_override"] = email_overrides[customer_id]

        cus_data[ModelCustomer._meta.pk.attname] = pk
        customer_object_list.append(ModelCustomer(**cus_data))
        cus_add_i += 1

    ModelAddress = _get_model("customers.addresses")
    address_object_list = []
    rows = []
    cus_adr_add_i = 0
    for adr in address:
        cus_id = adr[1]
        if not cus_pks.get(cus_id):
            continue

        cus_item = cus_pks[cus_id]
        # if cus_item['email'] in ['mitchba98@gmail.com', 'gnkholmes@gmail.com']:
        #     print(adr)
        #     print(cus_item)
        if cus_item["default_shipping"] is not None:
            if int(cus_item["default_shipping"]) == int(adr[0]):
                data = parse_customer_address(ModelAddress, cus_item, adr, "SHIP")
            elif cus_item["default_billing"] is not None:
                if int(cus_item["default_billing"]) == int(adr[0]):
                    data = parse_customer_address(ModelAddress, cus_item, adr, "BILL")
                else:
                    data = parse_customer_address(ModelAddress, cus_item, adr, "SHIP")
            else:
                data = parse_customer_address(ModelAddress, cus_item, adr, "SHIP")

        # print("Add address for this customer - %s" % cus_item["email"], data)
        address_object_list.append(ModelAddress(**data))
        cus_adr_add_i += 1

    bulk_create(ModelCustomer, customer_object_list, cus_add_i, "customer")
    bulk_create(ModelAddress, address_object_list, cus_adr_add_i, "customer address")
