import os
import sys
import time
from importlib import import_module

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, no_translations
from django.core.management.sql import emit_post_migrate_signal, emit_pre_migrate_signal


def load_fixture(path, app):
    try:
        call_command("loaddata", path, app_label=app)
    except:
        print(f"not loading in fixture {path} in app {app}")


class Command(BaseCommand):
    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        parser.add_argument(
            "--module",
            help="module name.",
        )
        super().add_arguments(parser)

    @no_translations
    def handle(self, *args, **options):
        if options.get("module"):
            module_name = options.get("module")
            migrate_app = self.load_command_class(module_name)
            migrate_app.execute()
        else:
            modules = [
                # "customers.migrate_pricelist_cpg",
                # "customers.migrate_company",
                "categories.migrate_category",
                "products.migrate_product",
                # "magento.migrate_customer",
                # "magento.migrate_favourites",
                # "magento.migrate_orders",
            ]

            message = {
                "customers.migrate_pricelist_cpg": "pricelist & closed purchase group",
                "customers.migrate_company": "customer companies",
                "categories.migrate_category": "categories",
                "products.migrate_product": "products",
                "magento.migrate_customer": "customers",
                "magento.migrate_favourites": "customer favourites",
                "magento.migrate_orders": "magento orders",
            }
            # load_fixture("group.json", "customers")
            # load_fixture("blogpost.json", "blog")

            for module_name in modules:
                print("Migrate %s \n" % message[module_name])
                migrate_app = self.load_command_class(module_name)
                migrate_app.execute()
                print("End Migrate \n")

    def load_command_class(self, name):
        """
        Given a command name and an application name, return the Command
        class instance. Allow all errors raised by the import process
        (ImportError, AttributeError) to propagate.
        """
        module = import_module("%s.%s" % ("odoo", name))
        return module
