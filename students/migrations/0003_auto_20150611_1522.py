# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("students", "0002_auto_20150611_1519")]

    operations = [
        migrations.AlterField(
            model_name="sectionrequirement",
            name="section",
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE, to="classes.Section"
            ),
        )
    ]
