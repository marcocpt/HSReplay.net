# -*- coding: utf-8 -*-
# Generated by Django 1.10a1 on 2016-06-17 09:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20160610_0644'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accountclaim',
            name='id',
            field=models.UUIDField(primary_key=True, serialize=False),
        ),
    ]