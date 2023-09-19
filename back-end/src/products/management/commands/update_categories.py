from django.core.management.base import BaseCommand
from ...models import Product

class Command(BaseCommand):
    help = 'Migration category field to categories field in Product model'

    def handle(self, *args, **options):
        products = Product.objects.all()
        for product in products:
            if product.category:
                product.categories.add(product.category)
                product.save()
                self.stdout.write(f"Updated categories for product {product.pk}")
            else:
                pass
