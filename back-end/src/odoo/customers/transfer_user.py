import psycopg2 as Database
from psycopg2.extras import DictCursor

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, models
from odoo.utils import _get_model, bulk_update


def get_rappid_user_history(conn):
    """SQL Query to get all history of users
    from Odoo database, returns dicts"""
    cursor = conn.cursor(cursor_factory=DictCursor)
    query_str = """SELECT res.ref, ru.login, e.create_date
        FROM rappid_user_history e
        INNER JOIN res_partner res ON res.id=e.partner_id::INTEGER
        INNER JOIN res_users ru ON ru.id = e.user_id::INTEGER
        WHERE e.create_date > NOW() - INTERVAL '3 minutes'
        AND e.transfer_type = 'website'
        ORDER BY e.create_date ASC
    """
    cursor.execute(query_str)
    result = cursor.fetchall()
    cursor.close()
    return result


def get_customers(Model, emails):
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).filter(email__in=emails)
    return queryset


def get_companies(codes):
    Model = _get_model("customers.company")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).filter(company_code__in=codes)
    if queryset.count():
        return {item.company_code: item for item in queryset.all()}
    return {}


def execute():
    # Connect to ODOO Databases
    conn = Database.connect(settings.ODOO_DB_URI)
    Model = _get_model("customers.customuser")
    trade_grp = _get_model("customers.groupextend").objects.get(group_code="TRADE")

    users = get_rappid_user_history(conn)
    up_object_list = []
    users_to_update = {}

    for row in users:
        item = dict(row)
        username = str(item["login"]).strip().lower()
        if username.find("@") == -1:
            continue
        ref = str(item["ref"]).strip()
        users_to_update[username] = ref

    user_objs = get_customers(Model, list(users_to_update.keys()))
    companies = get_companies(list(users_to_update.values()))

    # loop throught the user objs, if company exists then set that
    if user_objs.count():
        for obj in user_objs.all():
            login = str(obj.email).strip().lower()
            ref = users_to_update.get(login)
            if not companies.get(ref):
                continue

            company = companies[ref]
            setattr(obj, "company_id", company)
            setattr(obj, "group_id_id", trade_grp.id)  # make sure trade
            up_object_list.append(obj)

    bulk_update(Model, up_object_list, ["company_id"], len(up_object_list), "customers")
