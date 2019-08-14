"""
Admin interface for students application.
"""
#######################
from __future__ import print_function, unicode_literals

from classes.models import Course, Semester

#######################
from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.db import models

from .models import (
    History,
    RequirementTag,
    SectionRequirement,
    Student,
    Student_Registration,
    iclicker,
)
from .views.admin import AdminClasslistUploadFormView, AdminReportUploadFormView

# from django.utils.translation import ugettext_lazy as _

##############################################################


def mark_inactive(modeladmin, request, queryset):
    queryset.update(active=False)


mark_inactive.short_description = "Mark selected items as inactive"

##############################################################


class UsedRelatedValuesFilter(admin.SimpleListFilter):
    """
    A custom filter, so that we only see related values which are used.
    """

    # Define a subclass and set these appropriately:
    title = "SetThis"
    # the parameter_name is the name of the related field.
    parameter_name = "set_this"
    allow_none = True
    reverse = False
    model = object

    def object_label(self, o):
        """
        Override this to customize the labelling of the objects
        """
        return "{}".format(o)

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples (coded-value, title).
        """
        qs = model_admin.get_queryset(request)
        related_qs = self.model.objects.filter(
            pk__in=qs.values_list(self.parameter_name, flat=True)
        )
        lookups = [(o.pk, self.object_label(o)) for o in related_qs]
        if self.reverse:
            lookups.reverse()
        if self.allow_none:
            lookups.append(("(None)", "(None)"))
        return lookups

    def queryset(self, request, queryset):
        """
        Apply the filter to the existing queryset.
        """
        filter = self.value()
        filter_field = self.parameter_name
        if filter is None:
            return
        elif filter == "(None)":
            filter_field += "__isnull"
            filter_value = True
        else:
            filter_field += "__pk__exact"
            filter_value = filter
        return queryset.filter(**{filter_field: filter_value})


##############################################################


class TermFilter(UsedRelatedValuesFilter):
    """
    A custom filter so that we only see terms that are actually used.
    """

    title = "Term"
    parameter_name = "section__term"
    allow_none = False
    reverse = True
    model = Semester


##############################################################


class CourseFilter(UsedRelatedValuesFilter):
    """
    A custom filter so that we only see people which are actually used.
    """

    title = "Course"
    parameter_name = "section__course"
    allow_none = False
    model = Course

    def object_label(self, o):
        return o.label


##############################################################
##############################################################


class HistoryAdminForm(forms.ModelForm):
    class Meta:
        model = History
        widgets = {
            "annotation": forms.TextInput(attrs={"size": 16}),
            "message": forms.TextInput(attrs={"size": 100}),
        }
        exclude = []


class HistoryInline(admin.TabularInline):
    model = History
    fields = ("created", "annotation", "message")
    readonly_fields = ["created"]
    form = HistoryAdminForm
    extra = 1
    can_delete = False

    def get_queryset(self, request):
        qs = super(HistoryInline, self).get_queryset(request)
        return qs.none()


class StudentAdmin(admin.ModelAdmin):
    list_display = ["person", "student_number"]
    list_filter = ["active", "created", "modified"]
    list_select_related = True
    search_fields = ["person__cn", "person__username", "student_number"]
    ordering = ["person"]
    inlines = (HistoryInline,)
    raw_id_fields = ("person",)
    fields = (("active", "person", "student_number"),)


admin.site.register(Student, StudentAdmin)

##############################################################


class iclickerAdmin(admin.ModelAdmin):
    list_display = ["iclicker_id", "student", "active"]
    list_filter = ["active"]
    list_select_related = ["student__person"]
    search_fields = [
        "iclicker_id",
        "student__person__cn",
        "student__person__username",
        "student__student_number",
    ]
    actions = [mark_inactive]
    raw_id_fields = ("student",)


admin.site.register(iclicker, iclickerAdmin)

##############################################################


class StudentRegistrationAdmin(admin.ModelAdmin):
    list_display = ["student", "section", "status", "aurora_verified"]
    list_filter = [
        "active",
        "aurora_verified",
        "status",
        TermFilter,
        CourseFilter,
        "section__section_name",
        "created",
        "modified",
    ]
    list_select_related = [
        "student__person",
        "section__course__department",
        "section__instructor",
    ]
    search_fields = [
        "student__person__cn",
        "student__person__username",
        "student__student_number",
    ]
    actions = [mark_inactive]
    raw_id_fields = ("student", "section")

    def get_urls(self):
        """
        Extend the admin urls for this model.
        Provide a link by subclassing the admin change_form,
        and adding to the object-tools block.
        """
        classlist_upload_view = AdminClasslistUploadFormView.as_view()
        classlist_upload_view = self.admin_site.admin_view(classlist_upload_view)
        classlist_upload_view = permission_required(
            "students.add_student_registration"
        )(classlist_upload_view)

        report_upload_view = AdminReportUploadFormView.as_view()
        report_upload_view = self.admin_site.admin_view(report_upload_view)
        report_upload_view = permission_required("students.add_student_registration")(
            report_upload_view
        )

        urls = super(StudentRegistrationAdmin, self).get_urls()
        urls = [
            url(
                r"^classlist-upload/$",
                classlist_upload_view,
                name="students_classlist_upload",
                kwargs={"admin_options": self},
            ),
            url(
                r"^report-upload/$",
                report_upload_view,
                name="students_report_upload",
                kwargs={"admin_options": self},
            ),
        ] + urls
        return urls


admin.site.register(Student_Registration, StudentRegistrationAdmin)

##############################################################


class SectionRequirementAdmin(admin.ModelAdmin):
    list_display = ["__str__"]
    list_filter = ["active", "section__active", "requirements", "section__term"]
    list_select_related = [
        "section__course__department",
        "section__instructor",
        "section__term",
    ]
    ordering = ["section"]
    actions = [mark_inactive]


admin.site.register(SectionRequirement, SectionRequirementAdmin)

##############################################################

#
