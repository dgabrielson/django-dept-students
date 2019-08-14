"""
Models for students app
"""
################################################################
###############
from __future__ import print_function, unicode_literals

import datetime

from classes.models import Section, Semester
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from people.models import Person

from . import conf, utils
from .managers import (
    IClickerManager,
    RequirementCheckManager,
    RequirementTagManager,
    SectionRequirementManager,
    StudentManager,
    StudentRegistrationManager,
)

###############

################################################################


class StudentsBaseModel(models.Model):
    """
    An abstract base class.
    """

    active = models.BooleanField(default=True)
    created = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name="creation time"
    )
    modified = models.DateTimeField(
        auto_now=True, editable=False, verbose_name="last modification time"
    )

    class Meta:
        abstract = True


################################################################


@python_2_unicode_compatible
class Student(StudentsBaseModel):

    person = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        limit_choices_to={"active": True, "flags__slug": "student"},
        help_text='Only people with the "student" flag are shown',
    )
    student_number = models.IntegerField(unique=True)

    objects = StudentManager()

    class Meta:
        ordering = ["person"]

    @property
    def sn_comma_given(self):
        return self.person.sn + ", " + self.person.given_name

    @property
    def history(self):
        return "\n".join(["{}".format(h) for h in self.history_set.all()])

    def __str__(self):
        return self.sn_comma_given

    def History_Update(self, tag, info, subobj=None, action_flag=None, user=None):
        History.objects.create(student=self, annotation=tag, message=info)
        if conf.get("history:django_admin"):
            utils.admin_history(
                subobj or self, "{} [/{}]".format(info, tag), action_flag, user
            )

    def get_registrations(self):
        return Student_Registration.objects.filter(active=True, student=self).order_by(
            "section"
        )

    def get_registration(self, section):
        return Student_Registration.objects.get(
            active=True, student=self, section=section
        )

    def get_email_address(self):
        """
        Caution: this will retrieve non-public email addresses.
        """
        qs = self.person.emailaddress_set.filter(active=True)

        info = list(qs)  # force evalutation: 1 query.
        if not info:
            return None
        if any([i.preferred for i in info]):
            for i in info:
                if i.preferred:
                    return i.address
        return info[0].address


################################################################


class StudentsFKBaseModel(StudentsBaseModel):
    """
    An abstract base class.
    """

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, limit_choices_to={"active": True}
    )

    class Meta:
        abstract = True


################################################################


@python_2_unicode_compatible
class History(StudentsFKBaseModel):
    """
    A single student history entry.
    Once created, history items *should not* be altered.
    """

    annotation = models.CharField(max_length=128, blank=True)
    message = models.TextField()

    class Meta:
        ordering = ("-created",)
        verbose_name = "Student history"
        verbose_name_plural = "Student history"

    def __str__(self):
        if self.annotation:
            return "[{self.created} /{self.annotation}] {self.message}".format(
                self=self
            )
        else:
            return "[{self.created}] {self.message}".format(self=self)


################################################################


@python_2_unicode_compatible
class iclicker(
    StudentsFKBaseModel
):  # this should really be called "iclicker_registration" or some such.
    """
    Example WebSync:
    http://www.iclicker.com/iclickerregistration/GetRegistered.aspx?c=1bce01d4
    """

    iclicker_id = models.CharField(max_length=8, verbose_name="i>clicker ID")

    objects = IClickerManager()

    def __str__(self):
        return self.iclicker_id + ": " + self.student.person.cn

    class Meta:
        verbose_name = "iclicker"
        unique_together = [["iclicker_id", "student"]]


################################################################

STUDENT_STATUS_CHOICES = (
    ("AA", "Added by Instructor"),
    ("SA", "Auditing Student"),
    ("B", "WebAssign self-registration - account pending"),
    ("BA", "Self-registered"),
    ("CC", "WebAssign self-registration - account created"),
    ("N", "Blocked - wrong student number or wrong section"),
    ("O", "WebAssign account blocked - failed honesty declaration"),
    ("P", "WebAssign account NOT created - permission NOT given"),
    ("VW", "Voluntary Withdrawl"),
    ("AW", "Authorized Withdrawl"),
    ("CW", "Compulsary Withdrawl"),
    ("00", "Deregistered - end of term"),
    # note: __endswith='A' or __endswith='C' indicates validity.
    #       __endswith='W' or __endswith='0' indicates certain types of 'inactive' regs.
)
# 2 letters indicate a normal status,
#   a two letter status ending in 'W' or '0' indicates withdrawl or deregistration
#   a two letter status ending in 'A' indicates good standing.
# 1 letter indicates an error status or status that requires attention.

################################################################


@python_2_unicode_compatible
class Student_Registration(StudentsFKBaseModel):

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        limit_choices_to={"active": True},
        related_name="registration_list",
    )
    status = models.CharField(max_length=2, choices=STUDENT_STATUS_CHOICES, blank=True)
    aurora_verified = models.BooleanField(default=False)

    objects = StudentRegistrationManager()

    class Meta:
        verbose_name = "Student Registration"
        ordering = ["student"]
        unique_together = [
            [
                "student",
                "section",
            ]  # each student can have only one registration per section
        ]
        # db_table = 'fippa_student_registration'

    def __str__(self):
        return (
            "{}".format(self.student)
            + " / "
            + "{}".format(self.section)
            + " / "
            + self.get_status_display()
        )

    def good_standing(self):
        if self.active and self.student.active and self.section.active:
            if len(self.status) == 2 and self.status[1] in ["A", "C"]:
                return True
        return False

    def allow_webassign_registration(self):
        if not reg.section.Using_WebAssign:
            return False
        return self.good_standing() and self.status[1] == "A"

    def can_register_iclicker(self):
        if not self.good_standing():
            return False
        if not self.section.Using_iClicker:
            return False
        return self.status[1] == "C"

    def aurora_active(self):
        if not self.active:
            return False
        if not self.aurora_verified:
            return False
        if len(self.status) == 2 and self.status[1] in ["W", "0"]:
            return False
        return True

    def status_msg(self):
        if not self.good_standing():
            return self.get_status_display()
        return ""

    class Meta:
        verbose_name = "Student Registration"
        ordering = ["student"]
        unique_together = [
            [
                "student",
                "section",
            ]  # each student can have only one registration per section
        ]


################################################################


@python_2_unicode_compatible
class RequirementTag(StudentsBaseModel):
    """
    This simple model is provided for future extensions to the requirement
    system.
    """

    label = models.SlugField(unique=True)

    objects = RequirementTagManager()

    def __str__(self):
        return self.label


################################################################


@python_2_unicode_compatible
class SectionRequirement(StudentsBaseModel):
    """
    This is a simple intermediate table to define which sections
    have some kind of signup requirement
    (and thus, should be options in the form).
    """

    section = models.OneToOneField(Section, on_delete=models.CASCADE)

    requirements = models.ManyToManyField(
        RequirementTag,
        limit_choices_to={"active": True},
        help_text="Remember: requirements are set in " + "your site's settings file",
    )

    objects = SectionRequirementManager()

    def __str__(self):
        return "Requirements for " + "{}".format(self.section)


################################################################


@python_2_unicode_compatible
class RequirementCheck(StudentsBaseModel):
    """
    This is a simple intermediate table to define which requirements have
    been fulfilled by a student for a particular class.
    """

    registration = models.OneToOneField(
        Student_Registration,
        on_delete=models.CASCADE,
        limit_choices_to={"active": True},
    )

    requirements = models.ManyToManyField(
        RequirementTag, limit_choices_to={"active": True}
    )

    objects = RequirementCheckManager()

    def __str__(self):
        return "Requirements met for " + "{}".format(self.registration)

    def is_complete(self, label):
        return self.requirements.filter(label=label).count() > 0


################################################################
