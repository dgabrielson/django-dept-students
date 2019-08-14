# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("students", "0003_auto_20150611_1522")]

    operations = [
        migrations.AlterField(
            model_name="requirementcheck",
            name="registration",
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE, to="students.Student_Registration"
            ),
        )
    ]
