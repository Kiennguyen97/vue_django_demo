import json
import os
import uuid

import erppeek

from django.utils.text import slugify

client = erppeek.Client(
    os.getenv["ODOO_URL"], "amtech", os.getenv("ODOO_USR"), os.getenv("ODOO_PW")
)


uu = lambda: str(uuid.uuid4())
ids = lambda dict_list: [x["id"] for x in dict_list]


all_prods = client.ProductTemplate.search_read(
    [("is_website_use", "=", True), ("active", "=", True)],
    [
        "id",
        "name",
        "default_code",
        "retail_price",
        "carton_qty",
        "web_category_one",
        "features",
    ],
)

with open("odoo/categories/cats.json", "r") as f:
    cats = json.load(f)

cats = {x["fields"]["slug"]: x["pk"] for x in cats}
print(cats)
first_cat = list(cats.keys())[0]

prods_list = []
for item in all_prods:
    if item["web_category_one"]:
        cat_lookup = (
            slugify(item["web_category_one"][1].split("/")[-1])
            + "-"
            + str(item["web_category_one"][0])
        )
    else:
        cat_lookup = first_cat
    base_dict = {
        "model": "products.product",
        "pk": item["default_code"],
        "fields": {
            "name": item["name"],
            "slug": slugify(item["name"] + " " + str(item["id"])),
            "description_short": item["name"],
            "description_long": item["features"],
            "image_urls": "orient-rat-pic.jpg",
            "retail_price": item["retail_price"],
            "active": True,
            "badge_text": "",
            "delivery_timeframe": "",
            "video_title": "",
            "video_url": "https://youtu.be/s7hib8aGOFY,https://youtu.be/nLX6CbIvBeo",
            "carton_qty": "",
            "category_id": cats.get(cat_lookup, cats[first_cat]),
            "qty_order_limit": None,
            "file_download_link": "/static/img/rat-instructions.pdf",
            "file_download_image": "/static/img/orient-how-to.png",
        },
    }
    prods_list.append(base_dict)

with open("odoo/products/prods.json", "w") as f:
    json.dump(prods_list, f)
