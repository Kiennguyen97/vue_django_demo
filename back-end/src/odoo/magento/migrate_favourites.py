import json
import math
import os
import sys
import uuid

import mysql.connector

from django.apps import apps
from django.core.serializers import base
from django.core.serializers.base import DeserializationError
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError
from odoo.utils import _get_model, bulk_create, get_field_attname


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
        for item in queryset:
            items[item.uuid] = item
    return items


def get_customer():
    Model = _get_model("customers.customuser")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    if queryset.order_by().count() > 0:
        for item in queryset.select_related("company_id").all():
            items[item.email.lower()] = {"pk": item, "company_pk": item.company_id}
    return items


def get_products():
    Model = _get_model("products.product")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    if queryset.order_by().count() > 0:
        for item in queryset:
            items[str(item.sku).lower()] = item
    return items


uu = lambda: str(uuid.uuid4())


def get_uuid4():
    pk = uu()
    return pk


def get_favourites():
    conn = connection()
    db = conn.cursor()
    query_str = (
        "SELECT e.*, t1.email FROM %s AS e INNER JOIN %s AS t1 ON t1.entity_id = e.customer_id"
        % ("reorder_list", "customer_entity")
    )
    db.execute(query_str)
    fav_list = db.fetchall()
    conn.close()
    return fav_list


def get_favourites_groups():
    conn = connection()
    db = conn.cursor()
    query_str = "SELECT e.* FROM %s AS e" % ("reorder_group")
    db.execute(query_str)
    fav_groups = db.fetchall()
    conn.close()
    return fav_groups


def get_favourites_items():
    conn = connection()
    db = conn.cursor()
    query_str = "SELECT e.* FROM %s AS e" % ("reorder_item")
    db.execute(query_str)
    fav_items = db.fetchall()
    conn.close()
    return fav_items


def Deserializer(objects, **options):
    try:
        yield from PythonDeserializer(objects, **options)
    except (GeneratorExit, DeserializationError):
        raise
    except Exception as exc:
        raise DeserializationError() from exc


def execute():
    fav_items = get_favourites_items()
    fav_groups = get_favourites_groups()
    fav_list = get_favourites()
    customers = get_customer()
    products = get_products()

    items = []

    ModelFavList = _get_model("favourites.favouriteslist")
    fav_list_object = []
    fav_list_pks = {}
    fav_i = 0

    for item in fav_list:
        email = item[4].lower()
        try:
            cus_pk = customers[email]
            item_id = item[0]
            pk = get_uuid4()
            if item[3] is None:
                sequence = 0
            elif int(item[3]) < 0:
                sequence = 0
            else:
                sequence = math.ceil(item[3])
            data = {
                get_field_attname(ModelFavList, "name"): item[2],
                get_field_attname(ModelFavList, "sequence"): sequence,
                get_field_attname(ModelFavList, "user"): cus_pk["pk"].id,
                get_field_attname(ModelFavList, "company"): cus_pk["company_pk"].uuid
                if cus_pk["company_pk"] is not None
                else None,
            }
            fav_list_pks[item_id] = {"pk": pk, "cus_pk": cus_pk}
            data[ModelFavList._meta.pk.attname] = pk
            fav_list_object.append(ModelFavList(**data))
            fav_i += 1
        except KeyError:
            continue
    """
    try:
        objs = ModelFavList.objects.using(DEFAULT_DB_ALIAS).bulk_create(fav_list_object)
        for obj in objs:
            fav_list_exists[obj.uuid] = obj
        print("Installed %d favourite(s)\n" %i)
    except (DatabaseError, IntegrityError, ValueError) as e:
        print("Error loading favourite - %s " % e)
        raise
    """

    ModelFavGroup = _get_model("favourites.favouriteslistgroup")
    fav_group_object = []
    fav_group_pks = {}
    fav_group_exists = {}
    fav_g_i = 0
    for item in fav_groups:
        fav_list_id = item[1]
        try:
            fl_pks = fav_list_pks[fav_list_id]
            fav_list_pk = fl_pks["pk"]
            cus_pk = fl_pks["cus_pk"]
            pk = get_uuid4()
            item_id = item[0]
            if item[3] is None:
                sequence = 0
            elif int(item[3]) < 0:
                sequence = 0
            else:
                sequence = math.ceil(item[3])
            data = {
                get_field_attname(ModelFavGroup, "name"): item[2],
                get_field_attname(ModelFavGroup, "sequence"): sequence,
                get_field_attname(ModelFavGroup, "favourites_list"): fav_list_pk,
                get_field_attname(ModelFavGroup, "user"): cus_pk["pk"].id,
                get_field_attname(ModelFavGroup, "company"): cus_pk["company_pk"].uuid
                if cus_pk["company_pk"] is not None
                else None,
            }
            fav_group_pks[item_id] = {"pk": pk, "cus_pk": cus_pk}
            data[ModelFavGroup._meta.pk.attname] = pk
            fav_group_object.append(ModelFavGroup(**data))
            fav_g_i += 1
        except KeyError:
            continue

    """
    try:
        objs = ModelFavGroup.objects.using(DEFAULT_DB_ALIAS).bulk_create(fav_group_object)
        for obj in objs:
            fav_group_exists[obj.uuid] = obj
        print("Installed %d group favourite(s)\n" %i)
    except (DatabaseError, IntegrityError, ValueError) as e:
        print("Error loading group favourite - %s " % e)
        raise

    """

    insert_fav_items = {}
    ModelFavItem = _get_model("favourites.favouriteslistitem")
    fav_item_object = []
    fav_it_i = 0
    for item in fav_items:
        if item[7] is None:
            sequence = 0
        elif int(item[7]) < 0:
            sequence = 0
        else:
            sequence = math.ceil(item[7])
        fav_group_id = item[1]
        primary_key = item[2] + "_" + str(item[1])

        try:
            insert_fav_items[primary_key]
            continue
        except KeyError:
            insert_fav_items[primary_key] = True

        try:
            fg_pks = fav_group_pks[fav_group_id]
            fav_group_pk = fg_pks["pk"]
            cus_pk = fg_pks["cus_pk"]
            pk = get_uuid4()
            sku = str(item[2]).lower()
            if item[3] is None:
                max_qty = 0
            else:
                max_qty = math.ceil(item[3])
            data = {
                get_field_attname(ModelFavItem, "sequence"): sequence,
                get_field_attname(ModelFavItem, "favourites_group"): fav_group_pk,
                get_field_attname(ModelFavItem, "user"): cus_pk["pk"].id,
                get_field_attname(ModelFavItem, "note"): item[6],
                get_field_attname(ModelFavItem, "max_qty"): max_qty,
                get_field_attname(ModelFavItem, "product_id"): products[sku].sku,
                get_field_attname(ModelFavItem, "company"): cus_pk["company_pk"].uuid
                if cus_pk["company_pk"] is not None
                else None,
            }
            data[ModelFavItem._meta.pk.attname] = pk
            fav_item_object.append(ModelFavItem(**data))
            fav_it_i += 1
        except KeyError:
            continue

    bulk_create(ModelFavList, fav_list_object, fav_i, "favourite")
    bulk_create(ModelFavGroup, fav_group_object, fav_g_i, "group favourite")
    bulk_create(ModelFavItem, fav_item_object, fav_it_i, "favourite item")
    """
    try:
        objs = ModelFavItem.objects.using(DEFAULT_DB_ALIAS).bulk_create(fav_item_object)
        print("Installed %d favourite item(s)\n" %i)
    except (DatabaseError, IntegrityError, ValueError) as e:
        print("Error loading favourite item - %s " % e)
        raise
    """
