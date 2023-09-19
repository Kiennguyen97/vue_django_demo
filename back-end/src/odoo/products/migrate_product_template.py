import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.conf import settings
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError, models
from django.db.models import Q
from django.utils.text import slugify
from odoo.utils import _get_model, bulk_create, bulk_update

uu = lambda: str(uuid.uuid4())
p_temp_pk = lambda x: x.product_id + "_" + x.producttemplate_id


def get_products(Model):
    """Get all current products in django,
    returns dict with {sku: obj}"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    return queryset.all()


def get_products_template(Model):
    """Get all current products template in django,
    returns dict with {slug: obj}"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    return {x.slug: x for x in queryset.all()}


def get_products_template_product_rel(Model):
    """Get all current products template rel in django,
    returns dict with {sku_uuid: obj}"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    return {p_temp_pk(x): x for x in queryset.all()}


def parse_product_template_data(Model, obj):
    pk = uu()
    data = {
        "name": obj.name,
        "slug": obj.slug,
        "description": obj.description_long,
        "website_template": obj.website_template,
    }
    data[Model._meta.pk.attname] = pk
    return data


def execute():
    """Main Function"""
    # Connect DB of ODOO
    conn = Database.connect(settings.ODOO_DB_URI)
    cursor = conn.cursor(cursor_factory=DictCursor)
    group_sql = """SELECT
        gp.id,
        gp.description as name 
    FROM
        group_product gp
    """
    cursor.execute(group_sql)
    group_product_items = [dict(x)["id"] for x in cursor.fetchall()]
    cursor.close()

    ModelProdTemp = _get_model("products.producttemplate")
    ModelProdTempRel = _get_model("products.producttemplaterel")

    obj_queryset = (
        ModelProdTempRel.objects.using(DEFAULT_DB_ALIAS)
        .select_related("producttemplate")
        .filter(producttemplate__odoo_id__in=group_product_items)
    )
    items = {}
    for item in obj_queryset.all():
        if not items.get(item.producttemplate_id):
            rows = []
        else:
            rows = items[item.producttemplate_id]
        rows.append(item.product_id)
        items[item.producttemplate_id] = rows

    for producttemplate_id, product_ids in items.items():
        product_template_rel_queryset = ModelProdTempRel.objects.using(DEFAULT_DB_ALIAS).filter(
            ~Q(producttemplate_id=producttemplate_id), product_id__in=product_ids
        )
        ModelProdTemp.objects.using(DEFAULT_DB_ALIAS).filter(
            producttemplate_id__in=product_template_rel_queryset.values("producttemplate_id")
        ).delete()
        product_template_rel_queryset.delete()

    """
    Model = _get_model("products.product")
    ModelProdTemp = _get_model("products.producttemplate")
    ModelProdTempRel = _get_model("products.producttemplaterel")
    
    products = get_products(Model)
    products_temp = get_products_template(ModelProdTemp)
    p_temp_rel = get_products_template_product_rel(ModelProdTempRel)
    in_object_list = []
    up_object_list = []
    through_objs = []
    up_through_objs = []
    for obj in products:
        slug = obj.slug
        if not products_temp.get(slug):
            prod_temp_data = parse_product_template_data(ModelProdTemp, obj)
            in_object_list.append(ModelProdTemp(**prod_temp_data))
            through_objs.append(
                ModelProdTemp.product_ids.through(
                    producttemplate_id=prod_temp_data[ModelProdTemp._meta.pk.attname],
                    product_id=obj.sku,
                    sequence=obj.ordering
                )
            )
        else:
            existing_obj = products_temp[slug]
            pk_temp_rel = obj.sku + "_" + existing_obj.uuid
            if (
                obj.description_long != existing_obj.description or
                obj.website_template != existing_obj.website_template
            ):
                print("description", "needs updating from ", existing_obj.description, "to", obj.description_long)
                print("website_template", "needs updating from ", existing_obj.website_template, "to", obj.website_template)
                existing_obj.description = obj.description_long
                existing_obj.website_template = obj.website_template
                up_object_list.append(existing_obj)
            if p_temp_rel.get(pk_temp_rel):
                existing_obj_ptemp_rel = p_temp_rel[pk_temp_rel]
                if obj.ordering != existing_obj_ptemp_rel.sequence:
                    print("sequence", "needs updating from ", existing_obj_ptemp_rel.sequence, "to", obj.ordering)
                    existing_obj_ptemp_rel.sequence = obj.ordering
                    up_through_objs.append(existing_obj_ptemp_rel)


    bulk_create(ModelProdTemp, in_object_list, len(in_object_list), "Product Template")
    bulk_create(
        ModelProdTemp.product_ids.through,
        through_objs,
        len(through_objs),
        "Product Template linked products"
    )
    bulk_update(
        ModelProdTemp,
        up_object_list,
        ["description", "website_template"],
        len(up_object_list),
        "Product Template"
    )
    bulk_update(
        ModelProdTemp.product_ids.through,
        up_through_objs,
        ["sequence"],
        len(up_through_objs),
        "Product Template linked products"
    )
    """
