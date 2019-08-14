# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("classes", "0001_initial"), ("people", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="History",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
                ("annotation", models.CharField(max_length=128, blank=True)),
                ("message", models.TextField()),
            ],
            options={
                "ordering": ("-created",),
                "verbose_name": "Student history",
                "verbose_name_plural": "Student history",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="iclicker",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
                (
                    "iclicker_id",
                    models.CharField(max_length=8, verbose_name=b"i>clicker ID"),
                ),
            ],
            options={"verbose_name": "iclicker"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="RequirementCheck",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
            ],
            options={"abstract": False},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="RequirementTag",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
                ("label", models.SlugField(unique=True)),
            ],
            options={"abstract": False},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="SectionRequirement",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
                (
                    "requirements",
                    models.ManyToManyField(
                        help_text=b"Remember: requirements are set in your site's settings file",
                        to="students.RequirementTag",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        to="classes.Section",
                        unique=True,
                    ),
                ),
            ],
            options={"abstract": False},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
                ("student_number", models.IntegerField(unique=True)),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        to="people.Person",
                        help_text=b'Only people with the "student" flag are shown',
                        unique=True,
                    ),
                ),
            ],
            options={"ordering": ["person"]},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Student_Registration",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name=b"creation time"
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, verbose_name=b"last modification time"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        max_length=2,
                        choices=[
                            (b"AA", b"Added by Instructor"),
                            (b"SA", b"Auditing Student"),
                            (b"B", b"WebAssign self-registration - account pending"),
                            (b"BA", b"Self-registered"),
                            (b"CC", b"WebAssign self-registration - account created"),
                            (b"N", b"Blocked - wrong student number or wrong section"),
                            (
                                b"O",
                                b"WebAssign account blocked - failed honesty declaration",
                            ),
                            (
                                b"P",
                                b"WebAssign account NOT created - permission NOT given",
                            ),
                            (b"VW", b"Voluntary Withdrawl"),
                            (b"AW", b"Authorized Withdrawl"),
                            (b"CW", b"Compulsary Withdrawl"),
                            (b"00", b"Deregistered - end of term"),
                        ],
                    ),
                ),
                ("aurora_verified", models.BooleanField(default=False)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name=b"registration_list",
                        to="classes.Section",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE, to="students.Student"
                    ),
                ),
            ],
            options={"ordering": ["student"], "verbose_name": "Student Registration"},
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name="student_registration", unique_together=set([("student", "section")])
        ),
        migrations.AddField(
            model_name="requirementcheck",
            name="registration",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                to="students.Student_Registration",
                unique=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="requirementcheck",
            name="requirements",
            field=models.ManyToManyField(to="students.RequirementTag"),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="iclicker",
            name="student",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="students.Student"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="iclicker", unique_together=set([("iclicker_id", "student")])
        ),
        migrations.AddField(
            model_name="history",
            name="student",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to="students.Student"
            ),
            preserve_default=True,
        ),
    ]
