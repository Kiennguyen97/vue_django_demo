import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import erppeek
import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.apps import apps
from django.conf import settings
from django.core.serializers import base as serializers_base
from django.core.serializers.base import DeserializationError
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError
from django.utils.text import slugify
from odoo.utils import _get_model, bulk_create, bulk_update, requires_update

uu = lambda: str(uuid.uuid4())


def get_categories():
    Model = _get_model("products.category")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)

    if queryset:
        data = queryset.all()

        items = {int(x.odoo_id): x for x in data}
        rows = {int(x.odoo_id): x.uuid for x in data}
        slugs = {x.slug: True for x in data}
        return [items, rows, slugs]
    else:
        return ({}, {}, {})


def get_root_odoo_categories(conn):
    table = "web_categories"
    cursor = conn.cursor(cursor_factory=DictCursor)
    cat_id = settings.ODOO_ROOT_WEBCAT
    fields_str = "id, name, parent_category, hide_on_web, view_type"
    query_str = "SELECT %s FROM %s WHERE id = %s" % (fields_str, table, cat_id)
    cursor.execute(query_str)
    items = cursor.fetchall()
    cursor.close()
    root = dict(items[0])
    if root["hide_on_web"] != True:
        root["hide_on_web"] = False
    root["image_url"] = ""
    return root


def get_odoo_categories(conn):
    """Returns a nested dicts of the categories under root"""
    cursor = conn.cursor(cursor_factory=DictCursor)
    table = "web_categories"
    fields_str = "id, name, parent_category, hide_on_web, view_type"
    query_str = "SELECT %s FROM %s WHERE parent_category is NOT NULL" % (
        fields_str,
        table,
    )
    cursor.execute(query_str)
    results = [dict(x) for x in cursor.fetchall()]
    cursor.close()

    pic_items = get_category_images(conn)

    items = {}
    for item in results:
        if item["hide_on_web"] != True:
            item["hide_on_web"] = False
        parent_id = item["parent_category"]

        try:
            rows = items[parent_id]
        except KeyError:
            rows = {}

        cat_id = item["id"]
        item["image_url"] = ""
        if pic_items.get(cat_id):
            imgs = pic_items[cat_id]
            image_urls = []
            for img in imgs.values():
                image_urls.append(create_image_url(img))
            item["image_url"] = ",".join(image_urls)

        rows[item["id"]] = item
        items[parent_id] = rows
    return items


def get_category_images(conn):
    cursor = conn.cursor(cursor_factory=DictCursor)
    query_str = """
    SELECT ira.res_id,
    ira.id as img_id,
    cat.id as cat_id,
    ira.res_field,
    ira.mimetype, 
    ira.store_fname
    FROM ir_attachment ira
    INNER JOIN multi_image im ON im.id = ira.res_id
    INNER JOIN web_categories cat on im.category_id = cat.id
    WHERE im.category_id is NOT NULL
        AND ira.res_model = 'multi.image'
        AND ira.type = 'binary'
        AND ira.res_field in ('image_medium','image_small');
    """
    cursor.execute(query_str)
    results = cursor.fetchall()
    cursor.close()
    items = {}
    for x in results:
        item = dict(x)
        cat_id = item["cat_id"]
        if not items.get(cat_id):
            rows = {}
        else:
            rows = items[cat_id]

        res_id = item["res_id"]
        if not rows.get(res_id):
            rows[res_id] = item
        elif item["res_field"] == "image_medium":
            rows[res_id] = item
        items[cat_id] = rows
    return items


def create_image_url(img):
    fname = img["store_fname"][0:10]
    ext = img["mimetype"].split("/")[1]
    return fname + "." + ext


def parse_category_data(item):
    data = {
        "name": item["name"],
        "slug": slugify(item["name"]),
        "odoo_id": item["id"],
        "parent_category": item["parent_category"],
        "hide_on_web": item["hide_on_web"],
        "view_type": item["view_type"],
        "image_url": item["image_url"],
    }

    return data


def parse_insert_category_data(Model, item, parent=None):
    field = Model._meta.get_field("parent_category")
    data = {
        "name": item["name"],
        "slug": item["slug"],
        "odoo_id": item["odoo_id"],
        "hide_on_web": item["hide_on_web"],
        "view_type": item["view_type"],
        "image_url": item["image_url"],
    }

    data[field.attname] = parent
    data[Model._meta.pk.attname] = item["pk"]
    return Model(**data)


def parse_update_category_data(Model, obj, item, old_cat_items):
    field = Model._meta.get_field("parent_category")
    obj.name = item["name"]
    obj.view_type = item["view_type"]
    obj.hide_on_web = item["hide_on_web"]
    obj.image_url = item["image_url"]
    if item["parent_category"] is None:
        parent_up = None
    else:
        parent_up = old_cat_items[item["parent_category"]]
    setattr(obj, field.attname, parent_up)
    return obj


def get_categories_by_parent(items={}, parent_ids=[], level=0, rows={}):
    if len(parent_ids):
        rows_tmp = {}
        for parent_id in parent_ids:
            try:
                row = rows[parent_id]
                rows_tmp.update(row)
            except KeyError:
                pass
        items[level] = rows_tmp
        parent_ids = rows_tmp.keys()
        if len(parent_ids):
            level += 1
            get_categories_by_parent(items, parent_ids, level, rows)

        return items


def execute():
    """Main Function"""
    conn = Database.connect(os.getenv("ODOO_DB_URI"))

    root_cat = get_root_odoo_categories(conn)
    odoo_cat_items = {}
    fields = {
        "name": "name",
        "parent_category": "parent_category",
        "hide_on_web": "hide_on_web",
        "view_type": "view_type",
        "image_url": "image_url",
    }
    model_rel_fields = {"parent_category": "odoo_id"}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_object_list = {
            executor.submit(get_categories): "django_category",
            executor.submit(get_odoo_categories, conn=conn): "odoo_category",
        }
        future_objects = as_completed(future_object_list)
        for future in future_objects:
            type_object = future_object_list[future]
            if type_object == "django_category":
                old_cats = future.result()
            if type_object == "odoo_category":
                odoo_cat_items = future.result()

    Model = _get_model("products.category")
    up_i = 0
    update_object_list = []

    parent_ids = [root_cat["id"]]
    old_cat_odoo_ids, old_cat_pks, slug_exists = old_cats

    root_cat_data = parse_category_data(root_cat)

    # checks that the root category exists & doesn't need updating.
    if old_cat_item := old_cat_odoo_ids.get(root_cat_data["odoo_id"]):
        slug_exists[old_cat_item.slug] = True
        is_up = requires_update(Model, root_cat_data, old_cat_item, fields, model_rel_fields)
        if is_up:
            obj = parse_update_category_data(Model, old_cat_item, root_cat_data, old_cat_pks)
            update_object_list.append(obj)
            up_i += 1

    # if necessary, creates the root cat
    else:
        pk = uu()
        slug = root_cat_data["slug"]
        slug_exists[slug] = True
        root_cat_data["pk"] = pk
        obj = parse_insert_category_data(Model, root_cat_data)
        obj.save()
        old_cat_pks[root_cat_data["odoo_id"]] = pk

    items = get_categories_by_parent({}, parent_ids, 1, odoo_cat_items)
    for i in items:
        rows = items[i]
        for index in rows:
            row_data = parse_category_data(rows[index])
            old_cat_item = old_cat_odoo_ids.get(row_data["odoo_id"])

            if old_cat_item:  # if it currently exists in django
                is_up = requires_update(Model, row_data, old_cat_item, fields, model_rel_fields)
                if is_up:
                    obj = parse_update_category_data(Model, old_cat_item, row_data, old_cat_pks)
                    update_object_list.append(obj)
                    up_i += 1

            if not old_cat_item:  ## doesn't exist in django
                pk = uu()
                slug = row_data["slug"].lower()
                if slug_exists.get(slug):
                    slug = slug + "-" + str(row_data["odoo_id"])
                    if slug_exists.get(slug):
                        raise
                    else:
                        row_data["slug"] = slug

                slug_exists[slug] = True
                parent = old_cat_pks.get(row_data["parent_category"])
                row_data["pk"] = pk
                obj = parse_insert_category_data(Model, row_data, parent)
                obj.save()
                old_cat_pks[row_data["odoo_id"]] = pk

    bulk_update(Model, update_object_list, fields.values(), up_i, "categorie")
