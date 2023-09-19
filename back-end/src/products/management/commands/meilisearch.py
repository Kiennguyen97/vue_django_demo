from django.core.management.base import BaseCommand, no_translations
from django.conf import settings

class Command(BaseCommand):
    @no_translations
    def handle(self, *args, **options):
        from products.meili_search import client

        try:
            client.get_index(settings.MEILI_INDEDX)
        except Exception as e:
            client.create_index()

        try:
            client.reindex_all()
        except Exception as e:
            print(str(e))
