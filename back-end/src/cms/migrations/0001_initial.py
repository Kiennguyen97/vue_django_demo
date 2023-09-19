# Generated by Django 4.2 on 2023-04-26 23:06

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('uuid', models.CharField(max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=50)),
                ('email_address', models.EmailField(max_length=255, unique=True)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('phone_number', models.CharField(blank=True, max_length=15)),
                ('message', models.TextField(max_length=255)),
                ('order_number', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'ordering': ['-create_date'],
            },
        ),
        migrations.CreateModel(
            name='Subscribe',
            fields=[
                ('uuid', models.CharField(max_length=36, primary_key=True, serialize=False)),
                ('email_address', models.EmailField(max_length=255)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]