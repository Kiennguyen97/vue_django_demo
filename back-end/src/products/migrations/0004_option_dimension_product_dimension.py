# Generated by Django 4.2 on 2023-05-08 02:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_category_meta_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='option',
            name='dimension',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='dimension',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
