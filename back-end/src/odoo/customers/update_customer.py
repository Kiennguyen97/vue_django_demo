from django.db import DEFAULT_DB_ALIAS
from odoo.utils import _get_model, bulk_update


def get_customers(Model):
    """SQL Query to get all customers
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).filter(group_id__isnull=True)
    return queryset.all()


def get_group(Model):
    """SQL Query to get all customers
    from Django database, returns dicts"""

    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).filter(group_code="RETAIL")
    return queryset.first()


def execute():
    Model = _get_model("customers.customuser")
    customerGroup = _get_model("customers.groupextend")
    customers = get_customers(Model)
    retail_group = get_group(customerGroup)

    up_object_list = []
    if customers.count():
        for obj in customers:
            setattr(obj, "group_id", retail_group)
            up_object_list.append(obj)

    bulk_update(Model, up_object_list, ["group_id"], len(up_object_list), "update customers")
