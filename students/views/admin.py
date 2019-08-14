"""
Extended admin views for students appliation.
"""

################################################################
from __future__ import print_function, unicode_literals

from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic.edit import FormView

from ..forms import ClasslistCreateSectionUploadForm, StudentReportUploadForm
from ..mixins import AdminSiteViewMixin

################################################################


class AdminClasslistUploadFormView(AdminSiteViewMixin, FormView):
    template_name = "admin/students/student_registration/extra_form.html"
    form_class = ClasslistCreateSectionUploadForm
    success_url = reverse_lazy("admin:app_list", kwargs={"app_label": "students"})
    initial = {"create_section": True, "create_all_students": True}

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs["request_user"] = getattr(self.request, "user", None)
        return form_kwargs

    def form_valid(self, form):
        """
        Process successful form submission.
        """
        error_list = form.save()
        if error_list:
            messages.warning(
                self.request,
                _("Some students may not be able to login: ")
                + _(", ").join(error_list),
                fail_silently=True,
            )
        else:
            messages.success(
                self.request, _("Classlist uploaded successfully."), fail_silently=True
            )
        return super(AdminClasslistUploadFormView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        """
        Extend the context so the admin template works properly.
        """
        context = super().get_context_data(**kwargs)
        context.update(
            submit_button_label="Save", page_header="Upload Aurora Classlist"
        )
        return context


################################################################


class AdminReportUploadFormView(AdminSiteViewMixin, FormView):
    template_name = "admin/students/student_registration/extra_form.html"
    form_class = StudentReportUploadForm
    success_url = reverse_lazy("admin:app_list", kwargs={"app_label": "students"})

    def form_valid(self, form):
        """
        Process successful form submission.
        """
        result_data = form.save()
        invalid_logins = result_data.get("invalid_logins", None)
        saved_total = result_data["saved_student_count"]
        ignore_student_count = result_data["section_ignore_student_count"]
        if invalid_logins:
            messages.warning(
                self.request,
                _("Some students may not be able to login: ")
                + _(", ").join(error_list),
                fail_silently=True,
            )
        if ignore_student_count != 0:
            plural = "" if ignore_student_count == 1 else "s"
            messages.warning(
                self.request,
                _("Student{} ignored due to unknown section: ".format(plural))
                + "{}".format(ignore_student_count),
                fail_silently=True,
            )
        messages.success(
            self.request,
            _("Classlist uploaded successfully, {} students.".format(saved_total)),
            fail_silently=True,
        )
        return super(AdminReportUploadFormView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        """
        Extend the context so the admin template works properly.
        """
        context = super(AdminReportUploadFormView, self).get_context_data(**kwargs)
        context.update(submit_button_label="Save", page_header="Upload Aurora Report")
        return context


################################################################
