# Generated by Django 4.2 on 2023-05-09 20:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_alter_productoption_option_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoption',
            name='display_choice',
            field=models.CharField(choices=[('RECTANGLE', 'Rectangle'), ('RADIO', 'Radio')], default='RECTANGLE', max_length=25),
        ),
    ]
