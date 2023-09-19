import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.utils.text import slugify
from odoo.utils import _get_model


def get_product_brands(Model):
    """Get all current product brands in django,
    returns list"""
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS)
    return queryset.all()


def get_odoo_brands():
    conn = Database.connect(settings.ODOO_DB_URI)
    cursor = conn.cursor(cursor_factory=DictCursor)
    sql = """select id as odoo_id, name
        from product_brand
        """
    cursor.execute(sql)
    return [dict(x) for x in cursor.fetchall()]


def execute():
    """Main Function"""
    Model = _get_model("products.brand")

    odoo_brands = {
        slugify(x["name"]): {
            "odoo_id": x["odoo_id"],
            "name": x["name"].strip(),
            "slug": slugify(x["name"]),
        }
        for x in get_odoo_brands()
    }

    django_b = get_product_brands(Model)
    all_django_brands = {x.odoo_id: x for x in django_b}
    all_slugs = [x.slug for x in django_b]

    for _, item in odoo_brands.items():
        if dj_b := all_django_brands.get(item["odoo_id"]):
            if dj_b.name != item["name"]:
                dj_b.name = item["name"]
            if dj_b.slug != item["slug"]:
                if item["slug"] not in all_slugs:
                    dj_b.slug = item["slug"]
                else:
                    dj_b.slug = item["slug"] + "-" + str(item["odoo_id"])

                all_slugs.append(dj_b.slug)
                dj_b.save()

        else:
            if item["slug"] not in all_slugs:
                slug = item["slug"]
            else:
                slug = item["slug"] + "-" + str(item["odoo_id"])
            all_slugs.append(slug)
            dj_b = Model(name=item["name"], odoo_id=item["odoo_id"], slug=slug)
            dj_b.save()
