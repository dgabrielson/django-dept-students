from importlib import import_module

# Dynamic building of requirement urls and views.
from django.conf import settings
from django.conf.urls import include, url
from django.forms import Form

from . import views

urlpatterns = [
    url(r"^$", views.register, name="students-register-start"),
    url(r"^confirm/$", views.confirm, name="students-register-confirm"),
    url(r"^thanks/$", views.thanks, name="students-register-thanks"),
]

for label, form, template in getattr(
    settings, "STUDENTS_REGISTRATION_REQUIREMENTS", []
):
    if isinstance(form, Form):
        form_class = form
    else:
        mod_name, f_name = form.rsplit(".", 1)
        form_class = getattr(import_module(mod_name), f_name)

    urlpatterns.append(
        url(
            r"^%s/$" % label,
            views.extra_requirement,
            name=views.REQUIREMENT_BASENAME % label,
            kwargs={
                "label": label,
                "form_class": form_class,
                "template_name": template,
            },
        )
    )

urlpatterns.append(url(r"^iclicker/", include("students.iclicker.urls")))
