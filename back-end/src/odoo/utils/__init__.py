import csv
import itertools
from datetime import datetime
from decimal import Decimal
from io import BytesIO, TextIOWrapper
from pathlib import Path

from django.contrib import messages
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError, models
from django.db.models.fields import Field
from django.db.models.lookups import PatternLookup
from django.shortcuts import redirect

# from openpyxl import load_workbook


__all__ = [
    "bulk_create",
    "bulk_update",
    "bulk_delete" "check_length_fields",
    "has_update",
    "bulk_delete_multiple_fields" "_get_model",
    "get_field",
    "get_field_attname",
    "update_object",
    "requires_update",
    "redirect_account_dashboard",
    "File",
    "get_products",
]

import logging

logger = logging.getLogger(__name__)
from django.apps import apps
from django.core.serializers import base
from django.db import connection, reset_queries


def database_debug(func):
    """add this as a decorator to view
    database queries. only works in debug mode"""

    def inner_func(*args, **kwargs):
        reset_queries()
        results = func(*args, **kwargs)
        query_info = connection.queries
        print("function_name: {}".format(func.__name__))
        print("query_count: {}".format(len(query_info)))
        queries = ["{}\n".format(query["sql"]) for query in query_info]
        print("queries: \n{}".format("".join(queries)))
        return results

    return inner_func


def _get_model(model_identifier):
    """Look up a model from an "app_label.model_name" string."""
    try:
        return apps.get_model(model_identifier)
    except (LookupError, TypeError):
        raise base.DeserializationError("Invalid model identifier: '%s'" % model_identifier)


def chunks(iterable, size=5000):
    iterator = iter(iterable)
    for first in iterator:
        yield itertools.chain([first], itertools.islice(iterator, size - 1))


def bulk_create(Model, object_list, i, type):
    if len(object_list):
        for chunk in chunks(object_list, size=500):
            try:
                Model.objects.using(DEFAULT_DB_ALIAS).bulk_create(chunk)
                logger.info("%s %s(s) was synchronized successfully" % (i, type))
            except (DatabaseError, IntegrityError, ValueError) as e:
                logger.error("Error sync %s(s) - %s" % (type, e))
                raise


def bulk_update(Model, object_list, fields, i, type):
    if len(object_list):
        for chunk in chunks(object_list, size=500):
            try:
                Model.objects.using(DEFAULT_DB_ALIAS).bulk_update(chunk, fields)
                logger.info("%s %s(s) was updated successfully" % (i, type))
            except (DatabaseError, IntegrityError, ValueError) as e:
                logger.error("Error sync %s(s) - %s" % (type, e))
                raise


def bulk_delete(Model, field, values=[]):
    if len(values):
        filter_str = {"%s__in" % field: values}
        Model.objects.using(DEFAULT_DB_ALIAS).filter(**filter_str).delete()


def bulk_delete_multiple_fields(Model, fields, values={}):
    filter_object = {}
    for field in fields:
        field_value = values[field]
        if isinstance(field_value, list):
            filter_object["%s__in" % field] = field_value
        else:
            filter_object[field] = field_value

    Model.objects.using(DEFAULT_DB_ALIAS).filter(**filter_object).delete()


def check_length_fields(Model, fields):
    is_pass = True
    for (field_name, field_value) in fields.items():
        field = Model._meta.get_field(field_name)
        if field.max_length is not None:
            if isinstance(field_value, float) or field_value == None:
                continue
            if len(field_value) > field.max_length:
                logger.error(
                    "%s - value too long for type character varying(%s)"
                    % (
                        field_value,
                        field.max_length,
                    )
                )
                is_pass = False
    return is_pass


def requires_update(Model, item, old_item, fields, model_rel_fields={}):
    """Checks if the fields require update, returns True / False"""
    result = False
    for (field_name, field_value) in fields.items():
        field = Model._meta.get_field(field_value)
        if item[field_name] is None:
            val = False
        else:
            val = field.to_python(item[field_name])

        if field.remote_field and isinstance(field.remote_field, models.ManyToOneRel):
            obj = getattr(old_item, field_value)
            if obj is None:
                old_val = None
            else:
                old_val = getattr(obj, model_rel_fields[field_value])
        else:
            old_val = getattr(old_item, field_value)

        old_val = field.to_python(old_val)

        # if decimal, need to round, otherwise it will endlessly update
        if isinstance(old_val, Decimal) or isinstance(old_val, float):
            old_val = round(old_val, 2)

        if isinstance(val, Decimal) or isinstance(val, float):
            val = round(val, 2)

        # if both are falsy, don't update
        # occurs cos sometimes we have None and False
        if (not old_val) and (not val):
            pass
        else:
            if val != old_val:
                print(item[field_name], field, "needs updating from ", old_val, "to", val)
                result = True
                break
    return result


def update_object(Model, item, obj, fields, model_rels={}):
    """Update data for object, return object"""
    for (field_name, field_value) in fields.items():
        field = Model._meta.get_field(field_value)
        if field.remote_field and isinstance(field.remote_field, models.ManyToOneRel):
            if item[field_name] is None:
                setattr(obj, field_value, None)
            else:
                setattr(
                    obj,
                    field_value,
                    model_rels[field_value][item[field_name]],
                )
        else:
            setattr(obj, field_value, item[field_name])
    return obj


def get_field(Model, field_name):
    return Model._meta.get_field(field_name)


def get_field_attname(Model, field_name):
    field = get_field(Model, field_name)
    return field.attname


def redirect_account_dashboard(request, message):
    messages.error(request, message)
    return redirect("update_customer", pk=request.user.id)


@Field.register_lookup
class ILike(PatternLookup):
    """Django offers a wide variety of built-in lookups for filtering
    (for example, exact and icontains). Add ILIKE filter for postgres"""

    lookup_name = "ilike"

    def get_rhs_op(self, connection, rhs):
        return "ILIKE %s" % rhs


class BaseFile:
    def __init__(self, file, fields=[]):
        self.f = file
        self.header = ()
        self.data = [] or ()
        self.errors = []
        self.read()
        if len(fields):
            self.defaule_fields = fields
        else:
            self.defaule_fields = ["favourites_list", "favourites_group", "product"]
        self.check_fields()

    def add_error(self, error):
        self.errors.append(error)

    def get_errors(self):
        return self.errors

    def get_header_name(self, header_name):
        if header_name.find("favourites_list") != -1:
            return "favourites_list"
        if header_name.find("favourites_group") != -1:
            return "favourites_group"
        if header_name.find("product") != -1:
            return "product"
        if header_name.find("max_qty") != -1:
            return "max_qty"

        return header_name

    def check_fields(self):
        fields = self.get_fields()
        if len(fields) == 0:
            message_error = (
                "favourites_list, favourites_group, product columns must exist in import file"
            )
            self.add_error(message_error)
        else:
            requried_fields = set(self.defaule_fields) - set(fields)
            if len(list(requried_fields)):
                message_error = "%s column(s) must exist in import file" % ", ".join(
                    list(requried_fields)
                )
                self.add_error(message_error)


class XlsxFile(BaseFile):
    def read(self):
        wb = load_workbook(filename=BytesIO(self.f.read()))
        sheet = wb.active
        rows = list(sheet.rows)
        self.header = rows[0]
        rows.pop(0)
        self.data = rows

    def get_row_data(self, row, row_index):
        row_data = {}
        is_pass = True
        for i in range(len(self.header)):
            if (not row[i].value or row[i].value == "") and (self.header[i].value != "max_qty"):
                err = "The value of %s column does not exists, row %s" % (
                    self.header[i].value,
                    row_index,
                )
                self.add_error(err)
                is_pass = False
                break
            else:
                header_name = self.get_header_name(self.header[i].value)
                row_data[header_name] = row[i].value
        if not is_pass:
            return None
        return row_data

    def get_fields(self):
        fields = []
        for i in range(len(self.header)):
            header_name = self.get_header_name(self.header[i].value)
            if header_name:
                fields.append(header_name)
        return fields


class CsvFile(BaseFile):
    def read(self):
        stream = TextIOWrapper(self.f, encoding="utf-8")
        reader = csv.reader(stream)
        self.header = next(reader)
        self.data = reader

    def get_row_data(self, row, row_index):
        row_data = {}
        is_pass = True
        for i in range(len(self.header)):
            if (not row[i] or row[i] == "") and (self.header[i] != "max_qty"):
                err = "The value of %s column does not exists, row %s" % (
                    self.header[i],
                    row_index,
                )
                self.add_error(err)
                is_pass = False
                break
            else:
                header_name = self.get_header_name(self.header[i])
                row_data[header_name] = row[i]
        if not is_pass:
            return None
        return row_data

    def get_fields(self):
        fields = []
        for i in range(len(self.header)):
            header_name = self.get_header_name(self.header[i])
            if header_name:
                fields.append(header_name)
        return fields


class File:
    def __init__(self, file, fields=[]):
        self.f = file
        self.keys = []
        self.errors = []
        self.ext = None
        self.f_type = None
        self.fields = fields
        self.get_ext()
        self.execute()

    def __repr__(self):
        return "<%s>" % (self.f.name)

    def execute(self):
        if not self.allow_access():
            self.errors.append("Please choose a csv or excel file")
        else:
            self.read()

    def allow_access(self):
        ext = self.ext
        return ext.lower() in {"csv", "xlsx"}

    def get_ext(self):
        self.ext = self.f.name.split(".")[-1]

    def read(self):
        ext = self.ext
        if ext.lower() == "csv":
            self.f_type = CsvFile(self.f, self.fields)
        elif ext.lower() == "xlsx":
            self.f_type = XlsxFile(self.f, self.fields)

    def get_file_type(self):
        return self.f_type


def get_products():
    Model = _get_model("products.product")
    obj = Model._default_manager
    queryset = obj.using(DEFAULT_DB_ALIAS).order_by(Model._meta.pk.name)
    items = {}
    if queryset.order_by().count() > 0:
        for item in queryset:
            items[str(item.sku).lower()] = item
    return items
