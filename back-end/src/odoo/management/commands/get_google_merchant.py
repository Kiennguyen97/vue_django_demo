import csv

import html2text

from django.core.management.base import BaseCommand
from django.db import connection
from products.models import Product


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [dict(zip([col[0] for col in desc], row)) for row in cursor.fetchall()]


def get_availability(prod):
    if prod.availability == "IN_STOCK":
        return "in_stock"
    else:
        return "out_of_stock"


def parse_desc(h, x):
    return "".join(x for x in h.handle(x).replace("\n\n", "\n").lstrip("\n") if ord(x) < 128)


def get_brand(p):
    try:
        return p.brand.name
    except:
        return ""


class Command(BaseCommand):
    help = "Gets Product Data for Google Merchant Feed"

    def handle(self, *args, **options):
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_emphasis = True
        h.escape_all = True

        cursor = connection.cursor()
        sql = """
        select 
        pp.sku as id
        , pp.name as title
        , pp.slug as link
        , pp.description_long as description
        , pp.retail_price as price

        from products_product pp
        join products_producttemplaterel ptr on pp.sku = ptr.product_id
        join products_producttemplate pt on ptr.producttemplate_id = pt.uuid
        where pt.uuid in (
            select pt.uuid 
            from products_producttemplate pt
            join products_producttemplaterel ptr on ptr.producttemplate_id = pt.uuid
            join products_product pp on ptr.product_id = pp.sku
            where pp.sku in (
    'SH280',
    'DN328',
    'A456',
    'A356-200',
    'G1063',
    'A388',
    'G977',
    'A303',
    'WC340',
    'FAH225-100',
    'G530',
    'I209',
    'A266',
    'A358,',
    'DI2169',
    'PD100',
    'DN242',
    'SH159',
    'SH822',
    'SH162',
    'G1005',
    'DI770',
    'SH153',
    'SH170',
    'SOA12',
    'PD107',
    'WC697',
    'WC373',
    'A298',
    'WC372',
    'SH157',
    'PD108',
    'SH821',
    'SH537',
    'SH608',
    'DI703',
    'G535',
    'FAH460',
    'SH154',
    'SH824',
    'WC355',
    'B3050',
    'ST501',
    'SH557',
    'SH538',
    'SH459',
    'B3059',
    'G540',
    'DN246',
    'G1061',
    'SH158',
    'SH825',
    'TP901',
    'I276',
    'SH160',
    'FAH634',
    'SH163',
    'SH326',
    'SH152',
    'DN240',
    'SH151',
    'SH650',
    'FAH468A',
    'PPCW141',
    'FAH486A',
    'PPCW130',
    'B167',
    'I133',
    'B3052',
    'B3053',
    'B3054',
    'RES106',
    'RES107',
    'RES104',
    'I122',
    'I307',
    'I124',
    'I125',
    'I333',
    'I123',
    'FAH451',
    'FAH452',
    'FAH451-2',
    'FAH327',
    'I146',
    'I145',
    'I160',
    'ST101',
    'DI2247',
    'DI318',
    'SH651',
    'SH652',
    'A299',
    'A297',
    'SOA11',
    'SOA14',
    'SOA13',
    'SOA10',
    'DN241',
    'SH161',
    'WC374',
    'SH415',
    'SH329',
    'SH211',
    'SH156',
    'SH164',
    'G1034',
    'SH621',
    'SH539',
    'A308',
    'A305',
    'A421',
    'SH820',
    'SH822E',
    'B3049',
    'PD103',
    'PD102',
    'PD104',
    'B3056',
    'B3058',
    'B3057',
    'S3273GR',
    'S3273BLK',
    'S3273OR',
    'S3273PI',
    'S3273PU',
    'S3263BLK',
    'S3263GR',
    'S3263MB',
    'S3263PI',
    'S3263BL',
    'S3263RBW',
    'S3267BLK',
    'S3267GR',
    'S3267MB',
    'S3267P',
    'S3267R',
    'S3267BL',
    'S3505BK',
    'S3505BL',
    'S3505GR',
    'S3505RD',
    'SU442',
    'SU434',
    'SU435'
            )
          )
        """
        cursor.execute(sql)
        prods = dictfetchall(cursor)
        django_prods = {x.sku: x for x in Product.objects.all()}
        all_prods = []

        for prod in prods:
            dj_prod = django_prods[prod["id"]]
            prod["id"] = prod["id"]
            prod["title"] = prod["title"]
            prod["description"] = parse_desc(h, prod["description"])
            prod["link"] = "https://www.amtech.co.nz/product/" + prod["link"]
            prod["condition"] = "new"
            prod["price"] = str(round(float(prod["price"]) * 1.15, 2)) + " NZD"
            prod["image link"] = dj_prod.get_img_urls()[0]
            prod["availability"] = get_availability(dj_prod)
            prod["product_type"] = dj_prod.get_categories()
            prod["brand"] = get_brand(dj_prod)
            prod["age group"] = "adult"
            prod["gtin"] = ""
            prod["mtn"] = ""
            prod["google product category"] = ""
            prod["identifier exists"] = "no"

            all_prods.append(prod)

        with open("google_merchant.csv", "w") as f:
            w = csv.DictWriter(f, all_prods[0].keys())
            w.writeheader()
            for prod in all_prods:
                w.writerow(prod)
