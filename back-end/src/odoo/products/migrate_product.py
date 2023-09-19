import datetime as dt
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2 as Database
import pytz
from dateutil.relativedelta import relativedelta
from psycopg2.extras import DictCursor

from django.conf import settings
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError, models
from django.utils.text import slugify
from odoo.utils import (
    _get_model,
    bulk_create,
    bulk_delete,
    bulk_delete_multiple_fields,
    bulk_update,
    check_length_fields,
    requires_update,
)

uu = lambda: str(uuid.uuid4())
p_temp_pk = lambda x: x.product_id + "_" + x.producttemplate.slug
product_temp_pk = lambda x: x.product_id + "_" + x.producttemplate_id


def get_categories():
    """Get all current categories in django,
    returns list with [{odoo_id: uuid}, {uuid: obj}]"""
    Model = _get_model("products.category")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    rows = {}
    if queryset.order_by().count() > 0:
        for item in queryset.all():
            # get categpry uuid by odoo id
            items[item.odoo_id] = item.uuid
            # get category by uuid
            rows[item.uuid] = item
    return [items, rows]


def get_django_products(Model):
    """Get all current products and categories in django,
    returns list with [{sku: obj}, {sku: [category_id]}]"""

    obj = Model._default_manager
    category_ids = Model.category_ids.through.objects.using(DEFAULT_DB_ALIAS)
    prod_category_ids = {}
    prods = {}
    if category_ids:
        for item in category_ids.all():
            prod = str(item.product_id).strip()
            if not prod_category_ids.get(prod):
                rows = []
            else:
                rows = prod_category_ids[prod]
            rows.append(item.category_id)
            prod_category_ids[prod] = rows
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    if queryset:
        prods = {str(item.sku).strip(): item for item in queryset.all()}

    return [prods, prod_category_ids]


def get_django_product_template_rels(Model, ModelProdTemp):
    """Get all current product template like with product in django,
    returns list with [{odoo_id: [sku]}, {odoo_id: producttemplate_uuid}, {sku_slug: obj}]"""

    obj = Model._default_manager
    results = {}
    prod_temp_objs = {}
    ptemp_uuids = {}
    ptemp_slugs = {}
    all_prod_groups = []

    queryset = obj.using(DEFAULT_DB_ALIAS).select_related("producttemplate")
    if queryset:
        for item in queryset.all():
            ptemp_slug = item.producttemplate.slug
            # ptemp_slugs[ptemp_slug] = item.producttemplate.uuid
            if not prod_temp_objs.get(ptemp_slug):
                rows = []
            else:
                rows = prod_temp_objs[ptemp_slug]
            rows.append(item.product_id)
            if len(rows) > 1:
                all_prod_groups.append(ptemp_slug)
            prod_temp_objs[ptemp_slug] = rows

            results[p_temp_pk(item)] = item
            results[product_temp_pk(item)] = item

    queryset_temp = ModelProdTemp.all_objects
    if queryset_temp:
        ptemp_slugs = {obj.slug: obj.uuid for obj in ModelProdTemp.all_objects.all()}

    return [prod_temp_objs, ptemp_uuids, results, ptemp_slugs, all_prod_groups]


def get_django_brand(Model):
    """Get all current product brands in django,
    returns dict with {odoo_id: object} + {uuid: object} + {slug: True}"""
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).filter(odoo_id__gt=0)
    if queryset.count() > 0:
        results = {}
        for item in queryset.all():
            results[item.odoo_id] = item
            results[item.uuid] = item
            results["slug-" + str(item.slug).strip().lower()] = True
        return results
    else:
        return {}


def gen_db_query_datetime(datetime_obj):
    """Pass in a datetime object, will return a dt object for passing into a query param.\n
    Best used like 'SELECT * FROM table WHERE date>%s',datetime"""

    utc = pytz.timezone("UTC")
    nzt = pytz.timezone(settings.TIME_ZONE)

    if datetime_obj.tzinfo == None:
        # print("No timezone info given, assuming NZ")
        aware_datetime = datetime_obj.replace(tzinfo=nzt)
    else:
        aware_datetime = datetime_obj

    utc_datetime = aware_datetime.astimezone(tz=utc)
    return utc_datetime


def get_additional_product_images(cursor):
    sql = """SELECT ira.res_id,
        ira.id as img_id,
        ira.res_field,
        ira.mimetype, 
        ira.store_fname,
        TRIM(p.default_code) as sku
        FROM public.ir_attachment ira
        INNER JOIN multi_image ims ON ims.id = ira.res_id
        INNER JOIN product_template p ON p.id = ims.product
        WHERE ira.res_model = 'multi.image'
        AND ira.type = 'binary'
        AND ira.res_field in ('image_medium','image')
        AND p.default_code IS NOT NULL;
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    items = {}
    obj_exists = {}
    if results:
        for item in results:
            obj = dict(item)
            img_name = create_image_url(obj)

            if not obj_exists.get(obj["sku"]):
                obj_exists[obj["sku"]] = {obj["res_id"]: {obj["res_field"]: img_name}}
                items[obj["sku"]] = {"hi_res": [], "medium_res": []}

                if obj["res_field"] == "image":
                    items[obj["sku"]]["hi_res"].append(img_name)
                else:
                    items[obj["sku"]]["medium_res"].append(img_name)
            else:
                old_obj = obj_exists[obj["sku"]]
                if old_obj.get(obj["res_id"]):
                    obj_exists[obj["sku"]][obj["res_id"]][obj["res_field"]] = img_name
                    if obj["res_field"] == "image":
                        items[obj["sku"]]["hi_res"].append(img_name)
                    else:
                        items[obj["sku"]]["medium_res"].append(img_name)
                else:
                    obj_exists[obj["sku"]][obj["res_id"]] = {obj["res_field"]: img_name}
                    if obj["res_field"] == "image":
                        items[obj["sku"]]["hi_res"].append(img_name)
                    else:
                        items[obj["sku"]]["medium_res"].append(img_name)
    return items


def get_odoo_product_resources(cursor):
    sql = """SELECT 
        mpr.store_fname,
        mpr.mimetype,
        mpr.name as file_name,
        TRIM(p.default_code) as sku
        FROM multi_product_resource mpr
        INNER JOIN product_template p ON p.id = mpr.product
        WHERE p.default_code IS NOT NULL;
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    items = {}
    if results:
        for item in results:
            obj = dict(item)
            if obj["store_fname"]:
                img_name = create_image_url(obj)
                item_data = {"filename": obj["file_name"], "url": img_name}
                if not items.get(obj["sku"]):
                    items[obj["sku"]] = [item_data]
                else:
                    items[obj["sku"]].append(item_data)
    return items


def get_odoo_products(conn, get_all=False):
    """SQL Query to get all products, all product group
    from Odoo database, returns list of dicts"""

    cursor = conn.cursor(cursor_factory=DictCursor)
    datetime_obj = dt.datetime.today() - relativedelta(days=2)
    twodays = gen_db_query_datetime(datetime_obj)

    sql = """SELECT
        a.id,
        a.name,
        TRIM(a.default_code) as sku,
        a.retail_price::Float,
        a.carton_qty,
        a.features,
        a.list_price::Float,
        a.discount_price::Float,
        a.website_template,
        gpl.sequence_in_group as sequence,
        a.group_product_id,
        UPPER(a.web_access_view) as access_view,
        a.web_access_purchase AS access_purchase, 
        a.is_clearence as is_clearance,
        a.on_discount as is_discount,
        a.top_product as brand_promise,
        a.amtech_preferred_product as is_preferred,
        a.meta_search_keywords as meta_keywords,
        b.id as brand_id,
        a.sale_ok as active,
        a.benefits,
        CONCAT_WS(',',a.web_category_one, a.web_category_two
            ,a.web_category_three,a.web_category_four) as web_categories
    FROM
        product_template a
    LEFT JOIN 
        group_product_line gpl 
    ON 
        gpl.product_id = a.id AND gpl.group_id = a.group_product_id
    LEFT JOIN 
        product_brand b
    ON 
        b.id = a.product_brand_id
    WHERE 
        a.default_code is NOT NULL
        AND a.default_code != ''
        AND a.type = 'product'
    """
    # gets only below by default
    if get_all == False:
        sql += """AND a.list_price > 0
        AND a.active = True
        AND a.is_website_use = True"""

    cursor.execute(sql)

    items = [dict(x) for x in cursor.fetchall()]
    # pass it thru a dict to filter dupes
    items_dict = {x["sku"]: x for x in items}

    items = [x for _, x in items_dict.items()]

    group_sql = """SELECT
        gp.id,
        gp.description as name 
    FROM
        group_product gp
    """
    cursor.execute(group_sql)
    group_product_items = [dict(x) for x in cursor.fetchall()]

    pic_sql = """
    SELECT ira.res_id,
    ira.id as img_id,
    ira.res_field,
    TRIM(p.default_code) as sku,
    ira.mimetype, 
    ira.store_fname
    FROM ir_attachment ira
    INNER JOIN product_template p on ira.res_id = p.id
    WHERE
        ira.res_model = 'product.template'
        AND ira.type = 'binary'
        AND ira.res_field in ('image_medium','image_small','image')
        AND p.default_code IS NOT NULL;
    """
    cursor.execute(pic_sql)
    pic_items = [dict(x) for x in cursor.fetchall()]
    img_ids = {x["img_id"]: x for x in pic_items}
    pic_dict = {}

    # {'PW513': {'hi_res': ['55/555b06c.jpeg', 'c1/c152972.jpeg'], 'medium_res': ['3d/3d6c31d.jpeg', 'f0/f01965e.jpeg']}}
    additional_pic_items = get_additional_product_images(cursor)

    # {'PW513': [{'filename': 'Name', 'url': 55/555b06c.jpeg'}]}
    resources = get_odoo_product_resources(cursor)

    stock_sql = """
        SELECT 
            TRIM(a.default_code) as sku,
                sum(stock.qty_onhand::Float) as qty_onhand,
                sum(stock.qty_picked) as qty_picked,
                sum(stock.qty_sales::Float) as qty_sales
            FROM
                product_template a
                left join product_product pp on pp.product_tmpl_id = a.id 
            LEFT JOIN (
                SELECT sum(qoh.qty_onhand) as qty_onhand
                , sum(amnt.qty_picked) as qty_picked
                , sum(sales.qty_sales) as qty_sales
                , p.id as pp_id
                FROM product_product p
                    LEFT JOIN (
                        SELECT sum(stq.qty) as qty_onhand, pp.id
                        FROM stock_quant stq
                        INNER JOIN product_product pp on stq.product_id=pp.id
                        INNER JOIN stock_location sloc on stq.location_id=sloc.id
                        WHERE sloc.usage='internal'
                            AND sloc.id != 16
                        GROUP BY pp.id
                    ) as qoh ON qoh.id = p.id
                    LEFT JOIN (
                        SELECT sum(stm.product_uom_qty) as qty_picked, pp.id
                        FROM stock_move stm
                        INNER JOIN product_product pp on stm.product_id=pp.id
                        LEFT JOIN stock_picking stp on stm.picking_id=stp.id
                        WHERE stm.location_dest_id=16 AND stm.write_date>%(start_date)s
                            AND stm.state='done'
                        GROUP BY pp.id
                    ) as amnt on amnt.id = p.id
                    LEFT JOIN (
                        SELECT pp.id, sum(sm.product_uom_qty) as qty_sales
                        FROM stock_move sm
                        INNER JOIN product_product pp on sm.product_id = pp.id
                        WHERE sm.location_id = 15 AND sm.location_dest_id = 16
                            AND sm.state in ('waiting','confirmed', 'available','assigned')
                        GROUP BY pp.id
                    ) as sales on sales.id = p.id
                WHERE p.active
                GROUP BY p.id
            ) as stock ON stock.pp_id = pp.id
            Where a.default_code IS NOT NULL and a.type = 'product' and a.active
            GROUP BY a.default_code, a.id
    """

    cursor.execute(stock_sql, {"start_date": twodays})
    stock_items = {}
    for x in cursor.fetchall():
        stock_item = dict(x)
        stock_items[stock_item["sku"]] = stock_item

    # construct a dict like {'WC340', {'image_medium': 123, 'image_small': 321}}
    for pic in pic_items:
        if pic_dict.get(pic["sku"]):
            pic_dict[pic["sku"]][pic["res_field"]] = pic["img_id"]
        else:
            pic_dict[pic["sku"]] = {pic["res_field"]: pic["img_id"]}

    product_link_group_ids = {}

    for item in items:
        if not item["access_purchase"]:
            item["access_purchase"] = "OPEN"
        else:
            item["access_purchase"] = str(item["access_purchase"]).upper()

        if item["retail_price"] is None or item["retail_price"] == 0:
            item["retail_price"] = item["list_price"]
        if item["discount_price"] is None or item["retail_price"] == "":
            item["discount_price"] = 0

        if item["is_clearance"] != True:
            item["is_clearance"] = False
        if item["is_discount"] != True:
            item["is_discount"] = False
        if item["brand_promise"] is None:
            item["brand_promise"] = False
        if item["is_preferred"] is None:
            item["is_preferred"] = False
        if item["meta_keywords"] is None:
            item["meta_keywords"] = ""

        if item["active"] != True:
            item["active"] = False

        item_sku = item["sku"]
        if stock_items.get(item_sku):
            stock_item_data = stock_items[item_sku]

            if stock_item_data["qty_onhand"] is None:
                item["qty_onhand"] = round(0, 2)
            else:
                item["qty_onhand"] = round(stock_item_data["qty_onhand"], 2)

            if stock_item_data["qty_picked"] is None:
                item["qty_picked"] = 0
            else:
                item["qty_picked"] = float(round(stock_item_data["qty_picked"], 2))

            if stock_item_data["qty_sales"] is None:
                item["qty_sales"] = 0
            else:
                item["qty_sales"] = float(round(stock_item_data["qty_sales"], 2))
        else:
            item["qty_onhand"] = round(0, 2)
            item["qty_picked"] = 0
            item["qty_sales"] = 0

        soh = item["qty_onhand"] - item["qty_sales"]
        sod_2days = (item["qty_picked"] + 0.1) / 5

        if soh < 5 and item["qty_picked"] > settings.MIN_SOLD or soh <= 0:
            item["availability"] = "OUT_OF_STOCK"
        elif soh <= sod_2days:
            item["availability"] = "LOW_STOCK"
        else:
            item["availability"] = "IN_STOCK"

        if item["group_product_id"]:
            if not product_link_group_ids.get(item["group_product_id"]):
                rows = []
            else:
                rows = product_link_group_ids[item["group_product_id"]]
            rows.append(str(item["sku"]).strip())
            product_link_group_ids[item["group_product_id"]] = rows

        ### parse product images
        prod_pic = []
        prod_hi_res = []

        if pic_dict.get(item["sku"]):
            images = pic_dict[item["sku"]]
            if images.get("image"):
                prod_hi_res.append(create_image_url(img_ids[images["image"]]))
                if images.get("image_medium"):
                    prod_pic.append(create_image_url(img_ids[images["image_medium"]]))
                else:
                    prod_pic.append(create_image_url(img_ids[images["image_small"]]))

        if additional_pic_items.get(item["sku"]):
            additional_images = additional_pic_items[item["sku"]]
            if additional_images.get("hi_res"):
                prod_hi_res.extend(additional_images["hi_res"])
            if additional_images.get("hi_res"):
                prod_pic.extend(additional_images["medium_res"])

        item["image_urls"] = ",".join(prod_pic)
        item["image_hi_res"] = ",".join(prod_hi_res)
        ###

        ### parse product resources
        if resources.get(item["sku"]):
            item["resource_urls"] = json.dumps(resources[item["sku"]])
        else:
            item["resource_urls"] = ""
        ###

    cursor.close()
    return [items, group_product_items, product_link_group_ids]


def create_image_url(img):
    """Create image name for product, return string"""
    fname = img["store_fname"][0:10]
    ext = img["mimetype"].split("/")[1]
    return fname + "." + ext


def parse_product_data(Model, item, django_brands):
    """Create data for product, return dict"""
    data = {
        "name": item["name"],
        "retail_price": item["retail_price"],
        "carton_qty": item["carton_qty"],
        "description_long": item["features"],
        "list_price": item["list_price"],
        "description_short": item["name"],
        "image_urls": item["image_urls"],
        "image_hi_res": item["image_hi_res"],
        "access_view": item["access_view"] if item["access_view"] else "OPEN",
        "access_purchase": item["access_purchase"] if item["access_purchase"] else "OPEN",
        "is_clearance": item["is_clearance"],
        "brand_promise": item["brand_promise"],
        "is_preferred": item["is_preferred"],
        "meta_keywords": item["meta_keywords"],
        "website_template": item["website_template"],
        "qty_onhand": item["qty_onhand"],
        "qty_picked": item["qty_picked"],
        "qty_sales": item["qty_sales"],
        "availability": item["availability"],
        "resource_urls": item["resource_urls"],
        "benefits": item["benefits"],
        "is_discount": item["is_discount"],
        "discount_price": item["discount_price"],
    }
    data["active"] = item["active"]
    data[Model._meta.pk.attname] = str(item["sku"]).strip()
    data["slug"] = slugify(str(item["sku"]).strip() + " - " + item["name"])
    data["video_url"] = ""
    data["file_download_link"] = ""
    data["file_download_image"] = ""

    if django_brands.get(item["brand_id"]):
        data["brand_id"] = django_brands[item["brand_id"]].uuid
    else:
        data["brand_id"] = None

    return data


def execute():
    """Main Function"""
    # Connect DB of ODOO
    conn = Database.connect(settings.ODOO_DB_URI)
    ERRORS = []  ## wlil use this to email admin with errors

    # Get model
    Model = _get_model("products.product")
    ModelBrand = _get_model("products.brand")
    ModelProdTemp = _get_model("products.producttemplate")
    ModelProdTempRel = _get_model("products.producttemplaterel")

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_object_list = {
            executor.submit(get_categories): "django_category",
            executor.submit(get_django_products, Model): "django_product",
            executor.submit(get_django_brand, ModelBrand): "django_brand",
            executor.submit(get_odoo_products, conn=conn): "odoo_product",
            executor.submit(
                get_django_product_template_rels, ModelProdTempRel, ModelProdTemp
            ): "product_template",
        }
        future_objects = as_completed(future_object_list)
        for future in future_objects:
            type_object = future_object_list[future]
            if type_object == "django_category":
                django_cat_pks, django_cats = future.result()
            if type_object == "django_product":
                django_products, prod_category_ids = future.result()
            if type_object == "django_brand":
                django_brands = future.result()
            if type_object == "odoo_product":
                odoo_products, group_product_items, product_link_group_ids = future.result()
            if type_object == "product_template":
                (
                    prod_temp_objs,
                    ptemp_uuids,
                    product_templates,
                    ptemp_slugs,
                    all_prod_groups,
                ) = future.result()

    ## the first time we run it, we want to include all inactive codes
    ## as well, to bring them in
    ## they will then be marked as inactive on the next run
    if len(django_products) == 0:
        odoo_products, group_product_items, product_link_group_ids = get_odoo_products(
            conn=conn, get_all=True
        )

    brand_field = Model._meta.get_field("brand")
    insert_object_list = []
    update_object_list = []
    p_temp_in_list = []
    p_temp_up_list = []
    ptemp_up_list = []
    p_temp_through_objs = []
    through_objs = []
    add_i = 0
    up_i = 0
    up_ptemp_through_objs = []
    ## maps fields from odoo to django names
    ## fields_map and parse_product_data are possibly redundant
    ## fields_map is the fields that are checked (other fields might not update....)
    fields_map = {
        "name": "name",
        "description_long": "description_long",
        "description_short": "description_short",
        "retail_price": "retail_price",
        "active": "active",
        "list_price": "list_price",
        "image_urls": "image_urls",
        "image_hi_res": "image_hi_res",
        "access_view": "access_view",
        "access_purchase": "access_purchase",
        "is_clearance": "is_clearance",
        "brand_promise": "brand_promise",
        "is_preferred": "is_preferred",
        "meta_keywords": "meta_keywords",
        "website_template": "website_template",
        brand_field.attname: "brand",
        "qty_onhand": "qty_onhand",
        "qty_picked": "qty_picked",
        "qty_sales": "qty_sales",
        "availability": "availability",
        "resource_urls": "resource_urls",
        "benefits": "benefits",
        "is_discount": "is_discount",
        "discount_price": "discount_price",
    }

    model_rel_fields = {"brand": "uuid"}
    exists_prod_cats = {}
    delete_product_cats = {}
    exists_prods = {}
    exists_prod_group = {}
    ptemp_rel_delete = {}
    sequence_products = {}

    for item in odoo_products:
        sequence = 0 if not item["sequence"] else item["sequence"]
        odoo_data = parse_product_data(Model, item, django_brands)
        website_template = odoo_data["website_template"]
        is_pass = check_length_fields(Model, odoo_data)
        if not is_pass:
            ERRORS.append("FIELD LENGTH TOO LONG - " + json.dumps(odoo_data))
            print("FIELD LENGTH TOO LONG - ", odoo_data)
        if is_pass:
            prod_sku = str(item["sku"]).strip()
            sequence_products[prod_sku] = sequence

            # if not there, append to the insert list
            if not django_products.get(prod_sku):
                if not exists_prods.get(prod_sku):
                    exists_prods[prod_sku] = True
                    if item["web_categories"]:
                        odoo_catids = str(item["web_categories"]).split(",")
                        for cat_id in odoo_catids:
                            if django_cat_pks.get(int(cat_id)):
                                cat_uuid = django_cat_pks[int(cat_id)]
                                prod_cat_uuid = "%s_%s" % (prod_sku, cat_uuid)
                                if not exists_prod_cats.get(prod_cat_uuid):
                                    print(
                                        "Adding %s category for product"
                                        % django_cats[cat_uuid].name
                                    )
                                    through_objs.append(
                                        Model.category_ids.through(
                                            product_id=prod_sku,
                                            category_id=cat_uuid,
                                        )
                                    )
                                    exists_prod_cats[prod_cat_uuid] = True

                    insert_object_list.append(Model(**odoo_data))

                    # The producttemplate wont create when we create new simple product and it belong product group
                    if not item["group_product_id"]:
                        ptemp_slug = odoo_data["slug"]
                        # create product template relate with product if product does not exists
                        if ptemp_slugs.get(ptemp_slug):
                            existing_ptemp_uuid = ptemp_slugs[ptemp_slug]
                            p_temp_through_objs.append(
                                ModelProdTemp.product_ids.through(
                                    producttemplate_id=existing_ptemp_uuid,
                                    product_id=prod_sku,
                                    sequence=sequence,
                                )
                            )
                        else:
                            p_temp_pk = uu()
                            p_temp_data = {
                                "name": odoo_data["name"],
                                "slug": odoo_data["slug"],
                                "description": odoo_data["description_long"],
                                "website_template": odoo_data["website_template"],
                            }
                            p_temp_data[ModelProdTemp._meta.pk.attname] = p_temp_pk
                            p_temp_in_list.append(ModelProdTemp(**p_temp_data))
                            p_temp_through_objs.append(
                                ModelProdTemp.product_ids.through(
                                    producttemplate_id=p_temp_pk,
                                    product_id=prod_sku,
                                    sequence=sequence,
                                )
                            )
                    # exists_prods[prod_sku] = True
                    print("Adding Product Item", odoo_data["name"])
                    add_i += 1

            # otherwise, check if update needed
            else:
                existing_obj = django_products[prod_sku]
                ptemp_pk = existing_obj.sku + "_" + existing_obj.slug
                require_up = requires_update(
                    Model, odoo_data, existing_obj, fields_map, model_rel_fields
                )
                if product_templates.get(ptemp_pk):
                    existing_obj_ptemp = product_templates[ptemp_pk]
                    if existing_obj_ptemp.sequence != sequence:
                        print(
                            "Updating Product Template Like product",
                            existing_obj_ptemp.sequence,
                            "to",
                            sequence,
                        )
                        existing_obj_ptemp.sequence = sequence
                        up_ptemp_through_objs.append(existing_obj_ptemp)

                    if existing_obj_ptemp.producttemplate.website_template != website_template:
                        up_ptemp_data = {
                            ModelProdTemp._meta.pk.attname: existing_obj_ptemp.producttemplate.uuid,
                            "website_template": website_template,
                        }
                        print("Updating Product Template Item", up_ptemp_data)
                        ptemp_up_list.append(ModelProdTemp(**up_ptemp_data))
                else:
                    # When the simple product be removed from product group, the producttemplate will created
                    if not item["group_product_id"]:
                        ptemp_slug = odoo_data["slug"]
                        # create product template relate with product if product does not exists
                        if not ptemp_slugs.get(ptemp_slug):
                            """
                            existing_ptemp_uuid = ptemp_slugs[ptemp_slug]
                            p_temp_through_objs.append(
                                ModelProdTemp.product_ids.through(
                                    producttemplate_id=existing_ptemp_uuid,
                                    product_id=prod_sku,
                                    sequence=sequence,
                                )
                            )
                            """
                            # else:
                            p_temp_pk = uu()
                            p_temp_data = {
                                "name": odoo_data["name"],
                                "slug": odoo_data["slug"],
                                "description": odoo_data["description_long"],
                                "website_template": odoo_data["website_template"],
                            }
                            p_temp_data[ModelProdTemp._meta.pk.attname] = p_temp_pk
                            p_temp_in_list.append(ModelProdTemp(**p_temp_data))
                            p_temp_through_objs.append(
                                ModelProdTemp.product_ids.through(
                                    producttemplate_id=p_temp_pk,
                                    product_id=prod_sku,
                                    sequence=sequence,
                                )
                            )

                if require_up:
                    print("Updating Product Item", odoo_data["name"])
                    for (field_name, field_value) in fields_map.items():
                        field = Model._meta.get_field(field_value)

                        ## if it's a relational field - only catgories at this point
                        if field.remote_field and isinstance(
                            field.remote_field, models.ManyToOneRel
                        ):
                            if odoo_data.get(field_name) is None:
                                setattr(existing_obj, field_value, None)
                            else:
                                if field_value == "category_id":
                                    object_rel = django_cats
                                else:
                                    object_rel = django_brands
                                if object_rel.get(odoo_data[field_name]):
                                    setattr(
                                        existing_obj,
                                        field_value,
                                        object_rel[odoo_data[field_name]],
                                    )
                                else:
                                    print(f"Can't find {odoo_data[field_name]} for {field_name}")
                        else:
                            setattr(existing_obj, field_value, odoo_data[field_name])

                    update_object_list.append(existing_obj)
                    up_i += 1

                if not prod_category_ids.get(prod_sku):
                    if item["web_categories"]:
                        odoo_catids = str(item["web_categories"]).split(",")
                        for cat_id in odoo_catids:
                            if django_cat_pks.get(int(cat_id)):
                                cat_uuid = django_cat_pks[int(cat_id)]
                                prod_cat_uuid = "%s_%s" % (prod_sku, cat_uuid)
                                if not exists_prod_cats.get(prod_cat_uuid):
                                    print(
                                        "Adding %s category for product"
                                        % django_cats[cat_uuid].name
                                    )
                                    through_objs.append(
                                        Model.category_ids.through(
                                            product_id=prod_sku,
                                            category_id=cat_uuid,
                                        )
                                    )
                                    exists_prod_cats[prod_cat_uuid] = True
                else:
                    old_prod_cat_ids = prod_category_ids[prod_sku]
                    odoo_prod_cat_ids = []
                    if item["web_categories"]:
                        odoo_catids = str(item["web_categories"]).split(",")
                        for cat_id in odoo_catids:
                            if django_cat_pks.get(int(cat_id)):
                                cat_uuid = django_cat_pks[int(cat_id)]
                                if cat_uuid not in old_prod_cat_ids:
                                    prod_cat_uuid = "%s_%s" % (prod_sku, cat_uuid)
                                    if not exists_prod_cats.get(prod_cat_uuid):
                                        print(
                                            "Adding %s category for product"
                                            % django_cats[cat_uuid].name
                                        )
                                        through_objs.append(
                                            Model.category_ids.through(
                                                product_id=prod_sku,
                                                category_id=cat_uuid,
                                            )
                                        )
                                        exists_prod_cats[prod_cat_uuid] = True
                                else:
                                    odoo_prod_cat_ids.append(cat_uuid)

                    del_cat_ids = set(old_prod_cat_ids) - set(odoo_prod_cat_ids)
                    if len(del_cat_ids):
                        delete_product_cats[prod_sku] = list(del_cat_ids)
                        print("Remove categories for product", del_cat_ids)

    # check items present in django, but not in Odoo. Need to be marked active=False
    active_django_products = set(
        [str(x.sku).strip() for _, x in django_products.items() if x.active]
    )
    to_archive_skus = active_django_products - set([str(x["sku"]).strip() for x in odoo_products])
    for sku in to_archive_skus:
        print("Archiving ", sku)
        to_archive = django_products[str(sku).strip()]
        setattr(to_archive, "active", False)
        update_object_list.append(to_archive)

    delete_ptemp_ids = []
    # process for the group product
    insert_product_group_objs = []

    for item in group_product_items:
        prod_id = item["id"]
        prod_temp_slug = slugify(item["name"])
        insert_product_group_objs.append(prod_temp_slug)
        if not ptemp_slugs.get(prod_temp_slug):
            if product_link_group_ids.get(prod_id):
                print(f"Create new the group product - {item['name']}")
                p_temp_pk = uu()
                p_temp_data = {
                    "name": item["name"],
                    "slug": prod_temp_slug,
                    "description": "",
                    "website_template": "",
                    "odoo_id": prod_id,
                }
                p_temp_data[ModelProdTemp._meta.pk.attname] = p_temp_pk
                p_temp_in_list.append(ModelProdTemp(**p_temp_data))
                for prod_sku in product_link_group_ids[prod_id]:
                    if sequence_products.get(prod_sku):
                        p_temp_through_objs.append(
                            ModelProdTemp.product_ids.through(
                                producttemplate_id=p_temp_pk,
                                product_id=prod_sku,
                                sequence=sequence_products[prod_sku],
                            )
                        )
                        if django_products.get(prod_sku):
                            existing_obj = django_products[prod_sku]
                            ptemp_pk = existing_obj.sku + "_" + existing_obj.slug
                            if product_templates.get(ptemp_pk):
                                existing_obj_ptemp = product_templates[ptemp_pk]
                                print(
                                    f"Delete the product template - {existing_obj_ptemp.producttemplate.name}"
                                )
                                delete_ptemp_ids.append(existing_obj_ptemp.producttemplate.uuid)
        else:
            if product_link_group_ids.get(prod_id):
                new_ptemp_product = product_link_group_ids[prod_id]
                old_ptemp_product_rel = []
                if prod_temp_objs.get(prod_temp_slug):
                    old_ptemp_product_rel = prod_temp_objs[prod_temp_slug]
                ptemp_uuid = ptemp_slugs[prod_temp_slug]
                p_temp_data = {
                    "name": item["name"],
                }
                p_temp_data[ModelProdTemp._meta.pk.attname] = ptemp_uuid
                p_temp_up_list.append(ModelProdTemp(**p_temp_data))
                ptemp_product_rel_insert = set(new_ptemp_product) - set(old_ptemp_product_rel)
                ptemp_product_rel_delete = set(old_ptemp_product_rel) - set(new_ptemp_product)
                ptemp_product_rel_update = (
                    set(old_ptemp_product_rel) - ptemp_product_rel_insert - ptemp_product_rel_delete
                )
                if len(ptemp_product_rel_update):
                    for prod_sku in ptemp_product_rel_update:
                        if sequence_products.get(prod_sku):
                            ptemp_pk = prod_sku + "_" + ptemp_uuid
                            if product_templates.get(ptemp_pk):
                                existing_obj_ptemp = product_templates[ptemp_pk]
                                if existing_obj_ptemp.sequence != sequence_products[prod_sku]:
                                    print(
                                        "Updating Product Template Like product",
                                        existing_obj_ptemp.sequence,
                                        "to",
                                        sequence_products[prod_sku],
                                    )
                                    existing_obj_ptemp.sequence = sequence_products[prod_sku]
                                    up_ptemp_through_objs.append(existing_obj_ptemp)

                if len(ptemp_product_rel_insert):
                    print(
                        f"Add the products for group product - {item['name']}",
                        ptemp_product_rel_insert,
                    )
                    for prod_sku in ptemp_product_rel_insert:
                        ptemp_pk = prod_sku + "_" + ptemp_uuid
                        if not product_templates.get(ptemp_pk):
                            if sequence_products.get(prod_sku):
                                p_temp_through_objs.append(
                                    ModelProdTemp.product_ids.through(
                                        producttemplate_id=ptemp_uuid,
                                        product_id=prod_sku,
                                        sequence=sequence_products[prod_sku],
                                    )
                                )
                            if django_products.get(prod_sku):
                                existing_obj = django_products[prod_sku]
                                ptemp_pk = existing_obj.sku + "_" + existing_obj.slug
                                if product_templates.get(ptemp_pk):
                                    existing_obj_ptemp = product_templates[ptemp_pk]
                                    print(
                                        f"Delete the product template - {existing_obj_ptemp.producttemplate.name}"
                                    )
                                    delete_ptemp_ids.append(existing_obj_ptemp.producttemplate.uuid)

                if len(ptemp_product_rel_delete):
                    print(
                        f"Delete the products for group product - {item['name']}",
                        ptemp_product_rel_delete,
                    )
                    ptemp_rel_delete[ptemp_uuid] = list(ptemp_product_rel_delete)
            else:
                print(f"Delete the group product - {item['name']}")
                ptemp_uuid = ptemp_slugs[prod_temp_slug]
                delete_ptemp_ids.append(ptemp_uuid)

    del_product_groups_ids = set(all_prod_groups) - set(insert_product_group_objs)

    print(f"need to create prods of len {len(insert_object_list)}")
    bulk_create(Model, insert_object_list, add_i, "product")
    print(f"need to update prods of len {len(update_object_list)}")
    bulk_update(Model, update_object_list, fields_map.values(), up_i, "product")
    print(f"need to create category link with product of len {len(through_objs)}")
    bulk_create(Model.category_ids.through, through_objs, len(through_objs), "product category")
    if len(delete_product_cats):
        print(f"need to delete category dont link with product")
        for product_id, cat_ids in delete_product_cats.items():
            bulk_delete_multiple_fields(
                Model.category_ids.through,
                ["product_id", "category_id"],
                {"product_id": product_id, "category_id": cat_ids},
            )
    if len(ptemp_rel_delete):
        print(f"need to delete product template dont link with product")
        for producttemplate_id, product_ids in ptemp_rel_delete.items():
            bulk_delete_multiple_fields(
                ModelProdTemp.product_ids.through,
                ["producttemplate_id", "product_id"],
                {"producttemplate_id": producttemplate_id, "product_id": product_ids},
            )
    # remove any ProductTemplate which don't have products assigned to them
    if len(delete_ptemp_ids):
        print(f"need to delete product template by ID")
        bulk_delete(ModelProdTemp.product_ids.through, "producttemplate_id", delete_ptemp_ids)
        bulk_delete(ModelProdTemp, "uuid", delete_ptemp_ids)

    if len(del_product_groups_ids):
        print(f"need to delete product template by Slug", del_product_groups_ids)
        bulk_delete(ModelProdTemp, "slug", list(del_product_groups_ids))

    print(f"need to create product template of len {len(p_temp_in_list)}")
    bulk_create(ModelProdTemp, p_temp_in_list, len(p_temp_in_list), "Product Template")
    print(f"need to create product template link with product of len {len(p_temp_through_objs)}")
    bulk_create(
        ModelProdTemp.product_ids.through,
        p_temp_through_objs,
        len(p_temp_through_objs),
        "Product Template linked products",
    )
    print(f"need to update website_template for product template of len {len(ptemp_up_list)}")
    bulk_update(
        ModelProdTemp, ptemp_up_list, ["website_template"], len(ptemp_up_list), "Product Template"
    )
    print(f"need to update name for product template of len {len(p_temp_up_list)}")
    bulk_update(ModelProdTemp, p_temp_up_list, ["name"], len(p_temp_up_list), "Product Template")
    print(f"need to update sequence for product template of len {len(up_ptemp_through_objs)}")
    bulk_update(
        ModelProdTemp.product_ids.through,
        up_ptemp_through_objs,
        ["sequence"],
        len(up_ptemp_through_objs),
        "Product Template linked products",
    )
