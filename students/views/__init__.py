"""
Views for the students appliation.
"""
import re

from classes.models import Section, Semester
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from people.models import Person
from uofm import auth, uofmauth

from ..forms import ConfirmationForm, StudentForm
from ..models import RequirementCheck, SectionRequirement, Student, Student_Registration

REQUIREMENT_BASENAME = "students-regreq-%s"
REGISTRATION_THRESHOLD = 1.0

ALL_REQUIREMENTS = [
    e[0] for e in getattr(settings, "STUDENTS_REGISTRATION_REQUIREMENTS", [])
]


def next_requirement_redirect(student_reg, current_label):
    """
    Based on the student registration, and _from, determine the next page view.

    ``current_label` gives the current view name, and should be used to determine
    the next view name, if given.
    """
    req = SectionRequirement.objects.for_section(student_reg.section)
    check, created = RequirementCheck.objects.get_or_create(
        active=True, registration=student_reg
    )
    current_label_seen = False
    if current_label is None:
        current_label_seen = True

    for req_label in ALL_REQUIREMENTS:
        if (
            current_label_seen
            and req.has(req_label)
            and not check.is_complete(req_label)
        ):
            return REQUIREMENT_BASENAME % req_label
        if req_label == current_label:
            current_label_seen = True

    # all requirements satisfied.
    return "students-register-thanks"


def get_student_registration(request):
    """
    from the session, get enough information to construct the student
    registration object, or None.
    """
    if not "section_pk" in request.session:
        return None
    if not "student_pk" in request.session:
        return None
    # load registration
    try:
        registration = Student_Registration.objects.get(
            student__pk=request.session["student_pk"],
            section__pk=request.session["section_pk"],
            student__person__username=request.user.username.strip(),
        )
        return registration

    except Student_Registration.DoesNotExist:
        return None


def is_registration_open():
    section_list = SectionRequirement.objects.get_advertised_sections()
    return section_list.count() > 0
    # return Semester.objects.current_percent() < REGISTRATION_THRESHOLD


def is_blacklisted_user(user):
    """
    This should eventually be configurable code.
    For now, we disallow icm username registrations.
    """
    return re.match("^icm\d+", user.username) is not None


@auth.uofm_only
def register(request):

    initial_form_data = {}
    if "section_pk" in request.session:
        initial_form_data["Course_Section"] = request.session["section_pk"]

    student = None
    if request.method == "POST":
        form = StudentForm(request.user, request.POST)
        if form.is_valid():
            student = form.process()
            # store student & course_section for confirm view
            request.session["student_pk"] = student.pk
            request.session["section_pk"] = form.cleaned_data["course_section"]
            return HttpResponseRedirect(reverse("students-register-confirm"))
    else:
        form = StudentForm(request.user, initial=initial_form_data)
        student = form.student

    registration_open = is_registration_open()
    if settings.DEBUG:
        registration_open = True

    #     if not registration_open:
    #         # this causes two database hits.
    #         next_semester = Semester.objects.get_current().get_next()

    blacklisted_user = is_blacklisted_user(request.user)

    return render(request, "students/register.html", locals())


@auth.uofm_only
def confirm(request):
    if "section_pk" not in request.session or "student_pk" not in request.session:
        return HttpResponseRedirect(reverse("students-register-start"))

    # only confirm when this is a new registration
    reg = get_student_registration(request)
    if reg is not None:
        return HttpResponseRedirect(reverse(next_requirement_redirect(reg, None)))

    section = Section.objects.get(pk=request.session["section_pk"])
    student = Student.objects.get(pk=request.session["student_pk"])

    if request.method == "POST":
        if "Back" in request.POST:
            if request.POST["Back"] == "Back":
                return HttpResponseRedirect(reverse("students.views.register"))
        form = ConfirmationForm(student, section, request.POST)
        if form.is_valid():
            # process form: activate registration and update student History
            reg = form.process()
            # finish up: redirect
            return HttpResponseRedirect(reverse(next_requirement_redirect(reg, None)))
    else:
        form = ConfirmationForm(student, section)

    allow_back = True
    registration_open = is_registration_open()
    if settings.DEBUG:
        registration_open = True
    next_semester = Semester.objects.get_current().get_next()

    return render(request, "students/confirm.html", locals())


@auth.uofm_only
def extra_requirement(request, label, form_class, template_name):
    reg = get_student_registration(request)
    if reg is None:
        return HttpResponseRedirect(reverse("students-register-start"))

    if request.method == "POST":
        form = form_class(reg, request.POST)
        if form.is_valid():
            next_url = None
            if form.process():
                RequirementCheck.objects.add(reg, label)
            next_url = getattr(form, "next_url", None)
            if callable(next_url):
                next_url = next_url()
            if next_url is None:
                next_url = reverse(next_requirement_redirect(reg, label))
            return HttpResponseRedirect(next_url)
    else:
        form = form_class(reg)

    return render(request, template_name, locals())


@auth.uofm_only
def thanks(request):
    reg = get_student_registration(request)
    if reg is None:
        return HttpResponseRedirect(reverse("students-register-start"))

    return render(request, "students/thanks.html", locals())


#
