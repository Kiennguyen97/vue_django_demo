def get_rss_xml_template(xml):
    xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
    <channel>%(xml)s
    </channel>
</rss>"""
    data = {"xml": xml}
    return xml_template % data


def get_atom_xml_template(xml):
    xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:g="http://base.google.com/ns/1.0">%(xml)s
</feed>"""
    data = {"xml": xml}
    return xml_template % data


def get_rss_item_xml_template(obj, h):
    xml_template = """
        <item>
            <g:id>%(id)s</g:id>
            <g:title><![CDATA[%(name)s]]></g:title>
            <g:description><![CDATA[%(description)s]]></g:description>
            <g:link>%(link)s</g:link>
            <g:image_link>%(image_link)s</g:image_link>
            <g:condition>%(condition)s</g:condition>
            <g:availability>%(availability)s</g:availability>
            <g:price>%(price)s</g:price>
            <g:gtin>%(gtin)s</g:gtin>
            <g:brand><![CDATA[%(brand)s]]></g:brand>
            <g:mpn>%(mpn)s</g:mpn>
            <g:google_product_category>%(google_product_category)s</g:google_product_category>
            <g:product_type><![CDATA[%(product_type)s]]></g:product_type>
            <g:custom_label_0><![CDATA[%(custom_label)s]]></g:custom_label_0>
        </item>"""
    data = {
        "id": obj.sku,
        "name": obj.name,
        "description": parse_desc(h, obj.description_long),
        "link": "https://www.amtech.co.nz/product/" + obj.slug,
        "image_link": obj.get_img_urls()[0],
        "condition": "new",
        "availability": get_availability(obj),
        "price": str(round(float(obj.retail_price) * 1.15, 2)) + " NZD",
        "gtin": "",
        "brand": get_brand(obj),
        "mpn": "",
        "google_product_category": "",
        "product_type": obj.get_three_levels_categories(),
        "custom_label": obj.get_first_category_name(),
    }
    return xml_template % data


def get_atom_item_xml_template(obj, h):
    xml_template = """
    <entry>
        <g:id>%(id)s</g:id>
        <g:title><![CDATA[%(name)s]]></g:title>
        <g:description><![CDATA[%(description)s]]></g:description>
        <g:link>%(link)s</g:link>
        <g:image_link>%(image_link)s</g:image_link>
        <g:condition>%(condition)s</g:condition>
        <g:availability>%(availability)s</g:availability>
        <g:price>%(price)s</g:price>
        <g:gtin>%(gtin)s</g:gtin>
        <g:brand><![CDATA[%(brand)s]]></g:brand>
        <g:mpn>%(mpn)s</g:mpn>
        <g:google_product_category>%(google_product_category)s</g:google_product_category>
        <g:product_type><![CDATA[%(product_type)s]]></g:product_type>
        <g:custom_label_0><![CDATA[%(custom_label)s]]></g:custom_label_0>
    </entry>"""
    data = {
        "id": obj.sku,
        "name": obj.name,
        "description": parse_desc(h, obj.description_long),
        "link": "https://www.amtech.co.nz/product/" + obj.slug,
        "image_link": obj.get_img_urls()[0],
        "condition": "new",
        "availability": get_availability(obj),
        "price": str(round(float(obj.retail_price) * 1.15, 2)) + " NZD",
        "gtin": "",
        "brand": get_brand(obj),
        "mpn": "",
        "google_product_category": "",
        "product_type": obj.get_three_levels_categories(),
        "custom_label": obj.get_first_category_name(),
    }
    return xml_template % data


def get_availability(prod):
    if prod.availability == "IN_STOCK":
        return "in_stock"
    else:
        return "out_of_stock"


def parse_desc(h, x):
    if x:
        return "".join(x for x in h.handle(x).replace("\n\n", "\n").lstrip("\n") if ord(x) < 128)
    return ""


def get_brand(obj):
    if obj.brand:
        return obj.brand.name

    return ""


def execute(*args, **kwargs):
    import html2text

    from django.conf import settings
    from django.db.models import Q
    from products.models import Category, Product

    cat_queryset = Category.objects.filter(hide_on_web=False)
    exclude_cat_ids = settings.EXCLUDE_CAT_IDS
    include_cat_ids = settings.INCLUDE_CAT_IDS

    if kwargs.get("exclude_cat_ids"):
        exclude_cat_ids += eval(kwargs.get("exclude_cat_ids"))

    if kwargs.get("include_cat_ids"):
        include_cat_ids += eval(kwargs.get("include_cat_ids"))

    if len(exclude_cat_ids):
        cat_queryset = cat_queryset.filter(
            ~Q(uuid__in=exclude_cat_ids), ~Q(slug__in=exclude_cat_ids)
        )

    if len(include_cat_ids):
        cat_queryset = cat_queryset.filter(
            Q(uuid__in=include_cat_ids) | Q(slug__in=include_cat_ids)
        )

    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_emphasis = True
    h.escape_all = True
    xml_string = ""
    xml_format = kwargs.get("format") if kwargs.get("format") else settings.XML_FORMAT
    if not xml_format:
        raise Exception("Missing XML format. RSS 2.0 or Atom 1, please use --format rss or atom")

    product_queryset = Product.all_objects.select_related("brand").filter(
        active=True,
        access_view="OPEN",
        access_purchase="OPEN",
        category_ids__in=cat_queryset.values("uuid"),
    )

    if xml_format == "rss":
        for obj in product_queryset.all():
            xml_string += get_rss_item_xml_template(obj, h)
        xml = get_rss_xml_template(xml_string)
    elif xml_format == "atom":
        for obj in product_queryset.all():
            xml_string += get_atom_item_xml_template(obj, h)
        xml = get_atom_xml_template(xml_string)

    with open(settings.XML_FIELD, "w") as f:
        f.write(xml)
        f.close()
