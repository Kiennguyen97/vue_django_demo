import json
import os
import uuid
from pprint import pprint as pp

import erppeek

from django.utils.text import slugify

client = erppeek.Client(
    os.getenv("ODOO_URL"), "amtech", os.getenv("ODOO_USR"), os.getenv("ODOO_PW")
)

uu = lambda: str(uuid.uuid4())
ids = lambda dict_list: [x["id"] for x in dict_list]

custs = client.ResPartner.search_read(
    [("is_company", "=", True), ("customer", "=", True), ("ref", "!=", "")],
    ["id", "ref", "name", "phone"],
)

addresses = client.ResPartner.search_read(
    [
        ("parent_id", "in", [x["id"] for x in custs]),
        ("active", "=", True),
        ("is_rappidaddr_archived", "=", False),
        ("type", "in", ["invoice", "delivery"]),
    ],
    ["id", "parent_id", "name", "street", "street2", "city", "email", "type", "zip"],
)

address_map = {"delivery": "SHIP", "invoice": "BILL"}

filter_str = lambda x: "" if not x else x  # returns an empty string if False

lookup_dict = {}
to_create = []
addresses_to_create = []

for item in custs:
    cust_uuid = uu()
    to_create.append(
        {
            "model": "customers.company",
            "pk": cust_uuid,
            "fields": {
                "name": item["name"],
                "company_code": item["ref"],
                "phone_number": item["phone"],
            },
        }
    )
    lookup_dict[item["id"]] = cust_uuid

for addr in addresses:
    addresses_to_create.append(
        {
            "model": "customers.addresses",
            "pk": uu(),
            "fields": {
                "name": filter_str(addr["name"]),
                "street_address_1": filter_str(addr["street"]),
                "street_address_2": filter_str(addr["street2"]),
                "city": filter_str(addr["city"]),
                "email_address": filter_str(addr["email"]),
                "company_id": lookup_dict[addr["parent_id"][0]],
                "type_address": address_map[addr["type"]],
                "address_postal": filter_str(addr["zip"]),
            },
        }
    )

with open("odoo/customers/custs.json", "w") as f:
    json.dump(to_create, f, indent=4)

with open("odoo/customers/addresses.json", "w") as f:
    json.dump(addresses_to_create, f, indent=4)
