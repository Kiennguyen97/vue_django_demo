# Generated by Django 4.2 on 2023-07-20 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0018_alter_productoption_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='show_logo',
            field=models.BooleanField(default=False),
        ),
    ]
