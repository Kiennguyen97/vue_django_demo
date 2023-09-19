import psycopg2 as Database
from django_rq import job
from psycopg2.extras import DictCursor

import customers.models
from django.conf import settings
from django.db import models
from odoo.odoo_client import OdooClient as client
from products.utils import smtp_send


@job
def send_invitation_email(**kwargs):
    smtp_send(
        subject=kwargs["subject"],
        emails=kwargs["emails"],
        body=kwargs["body"],
        html_body=kwargs["html_body"],
    )


class Role(models.TextChoices):
    ADMIN = "admin"
    STAFF = "staff"


class InvitationStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def get_company_id_by_code(ref):
    # get all companies from Odoo
    conn = Database.connect(settings.ODOO_DB_URI)
    cursor = conn.cursor(cursor_factory=DictCursor)
    query_str = """SELECT id
        FROM res_partner e
        WHERE e.ref = %(ref)s
    """
    cursor.execute(query_str, {"ref": ref})

    odoo_id = cursor.fetchone()
    cursor.close()
    return odoo_id[0]


def sync_address_to_odoo(address_obj, *args, **kwargs):
    """Update or create address for company when edit or add on the django"""
    # mapping fields between django and odoo
    fields_map = {
        "name": "name",
        "street_address_1": "street",
        "street_address_2": "street2",
        "city": "city",
        "address_postal": "zip",
        "latitude": "latitude",
        "longitude": "longitude",
    }
    # get data, return dict
    data = {}
    for field_name, field_value in fields_map.items():
        data[field_value] = getattr(address_obj, field_name)

    odoo_id = address_obj.odoo_id
    # create new address
    if odoo_id == 0:
        company = address_obj.company_id
        # check and create new address if the company does exists
        if company and company.uuid:
            parent_id = get_company_id_by_code(company.company_code)
            data["parent_id"] = parent_id
            data["type"] = "delivery"
            res = client.Instance().ResPartner.create(data)
            add_obj = customers.models.Addresses.objects.get(uuid=address_obj.uuid)
            add_obj.odoo_id = res.id
            add_obj.save()
    else:
        client.Instance().ResPartner.write([odoo_id], data)
