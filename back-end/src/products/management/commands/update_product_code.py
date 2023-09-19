from django.core.management.base import BaseCommand
from ...models import Product

class Command(BaseCommand):
    help = 'Update the code field in the Product model based on the sku field'

    def handle(self, *args, **options):
        products = Product.objects.all()
        for product in products:
            # if no code and no options then set code to sku ( code required when no options )
            # if not product.code and product.productoptionrel_set.count() == 0:
            if product.sku != product.slug:
                product.code = product.sku
            else:
                product.code = None

            product.save()
            self.stdout.write(f"Updated code for product {product.pk}")
