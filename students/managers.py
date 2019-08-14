"""
Managers for the students application.
"""
################################################################

from classes.models import Section, Semester
from django.conf import settings
from django.db import models
from people.models import Person

from .querysets import IClickerQuerySet

################################################################

REGISTRATION_GRACE_DAYS = getattr(settings, "REGISTRATION_GRACE_DAYS", 0)

#######################################################################
#######################################################################
#######################################################################


class CustomQuerySetManager(models.Manager):
    """
    Custom Manager for an arbitrary model, just a wrapper for returning
    a custom QuerySet
    """

    queryset_class = models.query.QuerySet

    def get_queryset(self):
        """
        Return the custom QuerySet
        """
        return self.queryset_class(self.model)


#######################################################################
#######################################################################
#######################################################################


class StudentManager(CustomQuerySetManager):
    def active(self, **kwargs):
        return self.filter(active=True, **kwargs)

    def get_from_username(self, username):
        return self.get(person__username=username)

    def get_from_user(self, user):
        return self.get_from_username(user.username)

    def get_or_create_from_user(self, user, **kwargs):
        person, flag = Person.objects.get_or_create_from_user(user, guess_names=True)
        obj, created = self.get_or_create(person=person, **kwargs)
        obj.person.add_flag_by_name("student", "Student")
        return obj, created


################################################################


class StudentRegistrationManager(CustomQuerySetManager):
    def reg_list(self, **kwargs):
        """
        Returns the registrations with the appropriate filters applied from ``**kwargs``.

        Note that:
            * ``good_standing=True`` is a "magic"" kwarg that does the right thing.
            * ``aurora_active=True`` is a "magic" kwarg that does the right thing.

        This function only ever returns active registrations.
        """
        good_standing = kwargs.pop("good_standing", False)
        aurora_active = kwargs.pop("aurora_active", False)

        qs = self.filter(**kwargs)  # apply  filters.
        qs = qs.filter(active=True)  # active registrations
        qs = qs.filter(section__active=True)  # Only active sections
        qs = qs.filter(student__active=True)  # student is active
        if good_standing:
            qs = qs.filter(
                models.Q(status__endswith="A") | models.Q(status__endswith="C")
            )
        if aurora_active:
            qs = qs.filter(aurora_verified=True)
            qs = qs.exclude(
                models.Q(status__endswith="W") | models.Q(status__endswith="0")
            )
        qs = qs.order_by("student__person")
        return qs

    def get_current(self, good_standing=False, aurora_verified=False):
        """
        Returns a queryset for the *current* registrations.
        """
        kwargs = {
            "good_standing": good_standing,
            "aurora_verified": aurora_verified,
            "section__active": True,
            "section__term": Semester.objects.get_current(),
        }
        return self.reg_list()

    def get_students_pk(self, section, good_standing=False, aurora_verified=False):
        qs = self.reg_list(good_standing=good_standing, section=section)
        if aurora_verified:
            qs = qs.filter(aurora_verified=True)
        id_list = qs.values_list("student", flat=True)
        return id_list

    def get_students(self, section, good_standing=False, aurora_verified=False):
        """
        good_standing and aurora_verified indicate restrictions on which students to return.
        """
        from .models import Student

        id_list = self.get_students_pk(section, good_standing, aurora_verified)
        return Student.objects.filter(active=True, id__in=id_list)

    def enrollment_count(self, section, **kwargs):
        """
        Accepts the same kwargs as reg_list()
        """
        return self.reg_list(section=section, **kwargs).count()


################################################################


class RequirementTagManager(CustomQuerySetManager):
    def has(self, label, **kwargs):
        """
        True if the current qs has the given attribute, False otherwise.

        Typically this will be used from a
        SectionRequirement.objects.for_section() result.
        """
        return self.filter(active=True, label__iexact=label, **kwargs).count() > 0


################################################################


class SectionRequirementManager(CustomQuerySetManager):
    def get_current(self, **filters):
        """
        Return a queryset for the current mappings.
        """
        qs = self.filter(
            active=True,
            section__active=True,
            section__course__active=True,
            section__term__in=Semester.objects.get_current_qs(),
        )
        return qs.filter(**filters).select_related()

    def get_next_term(self, **filters):
        """
        Return a queryset for next term's mappings.
        """
        qs = self.filter(
            section__course__active=True,
            section__term__in=Semester.objects.get_next_qs(),
        )
        return qs.filter(**filters).select_related()

    def get_current_sections(self, **filters):
        """
        Return a queryset for the current sections which have a requirement.
        """
        return (
            Section.objects.active()
            .current(grace=REGISTRATION_GRACE_DAYS)
            .filter(sectionrequirement__active=True)
        )

    def get_next_term_sections(self, **filters):
        """
        Return a queryset for the sections next term which have a requirement.
        """
        qs = self.get_next_term(**filters)
        pk_list = qs.values_list("section", flat=True)
        return Section.objects.filter(pk__in=pk_list)

    def get_advertised_sections(self, **filters):
        """
        Return a queryset for the current sections which have a requirement.
        """
        return self.get_current_sections()

    def for_section(self, section):
        """
        Return the requirements queryset for the given section, if one exists.
        If it does not exist, return None.
        """
        from .models import SectionRequirement

        try:
            return self.get(active=True, section=section).requirements
        except SectionRequirement.DoesNotExist:
            return None

    def exists(self, section, label):
        """
        Returns True if the requirement exists, False otherwise.

        Example:
        if SectionRequirement.objects.exists(section, 'honesty'):
            pass
        """
        req = self.for_section(section)
        if req is None:
            return False
        return req.has(label)

    def sections_by_req(self, label):
        """
        Like get_advertised_sections(), but returns a queryset for the
        current sections which have a given requirement.
        """
        return self.get_advertised_sections(requirements__label=label)


################################################################


class RequirementCheckManager(CustomQuerySetManager):
    def add(self, registration, label):
        """
        Add the given tag to the satisified requirements list.
        Note that the RequirementTag with the given label must already exist.
        """
        from .models import RequirementTag

        check, created_flag = self.get_or_create(registration=registration)
        req = RequirementTag.objects.get(active=True, label=label)
        check.requirements.add(req)
        registration.student.History_Update(
            "requirements",
            "Requirement %s satisfied for %s" % (label, registration.section),
        )
        if not check.active:
            check.active = True
        check.save()
        registration.student.save()
        return check

    def is_complete(self, registration, label):
        return (
            self.filter(
                active=True, registration=registration, requirements__label=label
            ).count()
            > 0
        )


################################################################

# class IClickerManager(CustomQuerySetManager):
#     queryset_class = IClickerQuerySet

IClickerManager = IClickerQuerySet.as_manager

################################################################
