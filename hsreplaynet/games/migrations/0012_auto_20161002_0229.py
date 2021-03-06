# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-02 02:29
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import hsreplaynet.games.models
import hsreplaynet.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0011_auto_20160928_2304'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gamereplay',
            name='replay_xml',
            field=models.FileField(upload_to=hsreplaynet.games.models.generate_upload_path),
        ),
        migrations.AlterField(
            model_name='globalgameplayer',
            name='player_id',
            field=hsreplaynet.utils.fields.PlayerIDField(blank=True, choices=[(1, 1), (2, 2)], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(2)]),
        ),
    ]
