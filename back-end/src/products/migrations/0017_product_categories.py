# Generated by Django 4.2 on 2023-07-04 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0016_groupproduct_productoption_product_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='categories_all', to='products.category'),
        ),
    ]
