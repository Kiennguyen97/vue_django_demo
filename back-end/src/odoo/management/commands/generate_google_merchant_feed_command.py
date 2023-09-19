from importlib import import_module

from django.core.management.base import BaseCommand, CommandError, no_translations


class Command(BaseCommand):
    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        parser.add_argument(
            "--format",
            help="XML format.",
        )

        parser.add_argument(
            "--exclude_cat_ids",
            help="The exclude specific categories.",
        )

        parser.add_argument(
            "--include_cat_ids",
            help="The include specific categories.",
        )

        super().add_arguments(parser)

    def load_command_class(self, name):
        """
        Given a command name and an application name, return the Command
        class instance. Allow all errors raised by the import process
        (ImportError, AttributeError) to propagate.
        """
        module = import_module("%s.%s" % ("odoo", name))
        return module

    def handle(self, *args, **options):
        module_name = "products.generate_google_merchant_feed_xml"
        app = self.load_command_class(module_name)
        app.execute(*args, **options)
