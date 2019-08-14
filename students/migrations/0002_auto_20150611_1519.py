# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("students", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="person",
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE,
                to="people.Person",
                help_text=b'Only people with the "student" flag are shown',
            ),
        )
    ]
