################################################################

from classes.forms import CourseSectionInputWidget
from classes.models import Section
from django import forms
from django.conf import settings
from people.models import EmailAddress, Person

from .models import SectionRequirement, Student, Student_Registration, iclicker
from .utils.aurora2 import (
    AuroraException,
    InvalidCSVFormat,
    InvalidSection,
    WrongSection,
    read_section_queryset,
    update_registrations,
)
from .validators import validate_csv_file_extension

################################################################


class Course_Section_Field(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.sections = Section.objects.none()
        if "label" not in kwargs:
            kwargs["label"] = "Course & Section"
        if "widget" not in kwargs:
            kwargs["widget"] = CourseSectionInputWidget(self.sections)
        return super().__init__(self.sections, *args, **kwargs)

    def load_sections(self, sections):
        self.sections = sections
        self.widget.load_sections(sections)

    def clean(self, value):
        if self.required or value != "--":
            try:
                section_id = int(value)
            except:
                raise forms.ValidationError("Please select a course and section.")
            return section_id


################################################################


class StudentForm(forms.Form):

    course_section = Course_Section_Field()
    # Name = forms.CharField(max_length=200, label='Your Name')
    student_number = forms.IntegerField()
    email = forms.EmailField()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        try:
            self.student = Student.objects.get_from_user(user)
        except Student.DoesNotExist:
            self.student = None

        if "initial" in kwargs:
            initial = kwargs["initial"]
            # supplement
            if self.student:
                if "student_number" not in initial:
                    initial["student_number"] = self.student.student_number
                person = self.student.person
            else:
                person, flag = Person.objects.get_or_create_from_user(
                    user, guess_names=True
                )
            if "email" not in initial:
                # for privacy reasons, this is complicated.
                qs = person.emailaddress_set.filter(active=True)
                info = list(qs)  # force evalutation: 1 query.
                if not info:
                    initial["email"] = user.email
                elif any([i.preferred for i in info]):
                    for i in info:
                        if i.preferred:
                            initial["email"] = i.address
                            break
                else:
                    initial["email"] = info[0].address

        super().__init__(*args, **kwargs)
        # sections is strictly for determining how to display in the template.
        self.check_sections = True
        self.load_sections()

    def load_sections(self):
        self.sections = SectionRequirement.objects.get_advertised_sections()
        # useful for testing outside of the regular registration times:
        # if settings.DEBUG:
        #    self.sections = Section.objects.advertised()
        self.fields["course_section"].load_sections(self.sections)

    def clean_student_number(self):
        n = int(self.data["student_number"])
        s = str(n)
        # NOTE: leading '0's ARE VALID!!!
        if len(s) != 7 and len(self.data["student_number"]) != 7:
            raise forms.ValidationError("Please enter your 7 digit student number.")
        # validate the student number is unique
        student_list = Student.objects.filter(
            student_number=self.data["student_number"]
        )
        if student_list:
            existing_student = (
                student_list.get()
            )  # otherwise, this number is already not unique
            if existing_student != self.student:
                raise forms.ValidationError("Please contact your instructor.")
        # The facts were these:
        #   by allowing users to re-load their data, it is possible to update
        #   an existing student.  In this scenario, how do we test for uniqueness?
        return n

    def process(self):
        """
        Called when posting and after passing form.is_valid()
        """
        if self.student:
            # update
            student = self.student
            student_needs_save = False
            if not student.active:
                student.active = True
                student_needs_save = True
            if student.student_number != self.cleaned_data["student_number"]:
                student.student_number = self.cleaned_data["student_number"]
                student_needs_save = True
            if student_needs_save:
                student.save()
        else:
            # create
            student, created = Student.objects.get_or_create_from_user(
                self.user, student_number=self.cleaned_data["student_number"]
            )
            student.History_Update("students.views", "student record created.")
            student.save()

        if not student.person.active:
            student.person.active = True
            student.person.save()

        student.person.add_email(self.cleaned_data["email"], "work", preferred=True)
        return student


################################################################


class ConfirmationForm(forms.Form):

    CRN = forms.CharField(max_length=10, label="CRN")

    def __init__(self, student, section, *args, **kwargs):
        self.student = student
        self.section = section
        super().__init__(*args, **kwargs)

    def clean_CRN(self):
        if self.section.crn.lower() != self.data["CRN"].lower():
            raise forms.ValidationError(
                "This is not the CRN for the course you selected."
            )
        return self.section.crn

    def process(self):
        """
        process a valid form.
        is_valid() is assumed True,
        An existing registration is assumed to not exist.
        """
        reg, flag = Student_Registration.objects.get_or_create(
            student=self.student, section=self.section, defaults={"status": "BA"}
        )
        if not reg.active:
            reg.active = True
            reg.save()
            self.student.History_Update(
                "students.views", "Self registration reactivated for %s" % self.section
            )
        else:
            self.student.History_Update(
                "students.views", "Self registration for %s" % self.section
            )
        self.student.save()
        return reg


################################################################


class HonestyForm(forms.Form):

    all_work = forms.BooleanField(
        required=True,
        initial=False,
        label="I declare that all work for this course is wholly my own work.",
    )
    not_copied_people = forms.BooleanField(
        required=True,
        initial=False,
        label="I declare that no part of my work has been "
        "*copied* by manual or electronic means from any work "
        "produced by any other person(s), past or present, "
        "except as directly authorized by the instructor.",
    )
    excused = forms.BooleanField(
        required=True,
        initial=False,
        label="I declare that no part of my work has been "
        "based on laboratory work that I *did not complete* "
        "due to unexcused absense(s), "
        "except as directly authorized by the instructor.",
    )
    no_team = forms.BooleanField(
        required=True,
        initial=False,
        label="I declare that no part of my work has been "
        "produced by several students working together at a time (this includes "
        "one person who provides any portion of an assignment to another "
        "student or students), "
        "except as directly authorized by the instructor.",
    )
    not_copied_other = forms.BooleanField(
        required=True,
        initial=False,
        label="I declare that no part of my work has been "
        "*copied* from any other source including textbooks "
        "and web sites, "
        "except as directly authorized by the instructor.",
    )
    not_modified = forms.BooleanField(
        required=True,
        initial=False,
        label="I declare that no part of my work has been "
        "*modified* to contain falsified data, "
        "except as directly authorized by the instructor.",
    )
    i_understand = forms.BooleanField(
        required=True,
        initial=False,
        label="I understand that penalties for submitting work which is not "
        "wholly my own, or distributing my work other students, may result in "
        "penalties under the University of Manitoba's "
        "Student Discipline Bylaw(\\*).",
    )

    def __init__(self, student_registration, *args, **kwargs):
        """
        Always override init to take the student registration.

        This is the simplest type of requirement form.
        Requirements forms can define either a next_url attribute
        or callable to short-circuit the registration process.
        If used, this should only be done LAST.
        """
        self.student_registration = student_registration
        super().__init__(*args, **kwargs)

    def process(self):
        """
        Always define the process function, which is only called when
        the form is valid.  This function does any required post-processing
        for the registration step.

        It should return True, if this step should be marked as a satisfied
        requirement, or False, if this step should *not* be marked as
        satisfied.
        """
        return True


################################################################


class DontShowForm(forms.Form):
    """
    This is a special requirement form which is used to deliver informational
    messages only.
    """

    not_again = forms.BooleanField(label="Don't show this again", required=False)

    def __init__(self, student_registration, *args, **kwargs):
        """
        Always override init to take the student registration.
        """
        self.student_registration = student_registration
        super().__init__(*args, **kwargs)
        # always make don't show last:
        k, v = self.fields.popitem()
        self.fields[k] = v

    def process(self):
        """
        Always define the process function, which is only called when
        the form is valid.  This function does any required post-processing
        for the registration step.

        It should return True, if this step should be marked as a satisfied
        requirement, or False, if this step should *not* be marked as
        satisfied.
        """
        return self.cleaned_data["not_again"]


################################################################


class iClickerForm(forms.Form):

    Remote_ID = forms.CharField(max_length=8, required=False, label="Remote ID")

    def __init__(self, student_registration, *args, **kwargs):
        """
        Always override init to take the student registration.
        """
        self.student_registration = student_registration
        self.iclicker_list = iclicker.objects.filter(
            student=student_registration.student
        ).order_by("-created")
        if self.iclicker_list:
            kwargs["initial"] = {"Remote_ID": self.iclicker_list[0].iclicker_id}

        super().__init__(*args, **kwargs)

    def process(self):
        """
        Always define the process function, which is only called when
        the form is valid.  This function does any required post-processing
        for the registration step.

        It should return True, if this step should be marked as a satisfied
        requirement, or False, if this step should *not* be marked as
        satisfied.
        """
        iclicker_id = self.cleaned_data["Remote_ID"]
        student = self.student_registration.student
        if iclicker_id:
            found = False
            for iclicker_map in self.iclicker_list.filter(iclicker_id=iclicker_id):
                found = True
                if not iclicker_map.active:
                    iclicker_map.active = True
                    iclicker_map.save()
                    student.History_Update(
                        "students.forms.iClickerForm",
                        "student reactivated their iclicker registration "
                        + iclicker_id,
                    )
                    student.save()
            if not found:
                iclicker_map = iclicker(student=student, iclicker_id=iclicker_id)
                iclicker_map.save()
                student.History_Update(
                    "students.views",
                    "student updated their iclicker to " + iclicker_id,
                    user=None,
                )
                student.save()

        return False  # ALWAYS show i>clicker registration.

    def clean_Remote_ID(self):

        if self.data["Remote_ID"] == "":
            return ""

        if len(self.data["Remote_ID"]) != 8:
            raise forms.ValidationError(
                "Your Remote ID is a series of 8 numbers and letters."
            )
        try:
            n = int(self.data["Remote_ID"], 16)
        except ValueError:
            raise forms.ValidationError(
                "Your Remote ID is a series of 8 numbers and letters."
            )

        return self.data["Remote_ID"].lower()

    def clean(self, *args, **kwargs):
        if (
            self.data["Remote_ID"] == ""
            and "not_again" in self.data
            and self.data["not_again"]
        ):
            raise forms.ValidationError("You must have an Remote ID to skip this page.")
        return super().clean()


################################################################


class ClasslistUploadForm(forms.Form):
    """
    For uploading aurora classlists; i.e., to populate
    StudentRegistrations (and Students).

    You may consider subclassing this form based on your needs.
    """

    classlist_file = forms.FileField(
        label="Classlist from Aurora",
        help_text="Classlist from Aurora (do not upload a modified classlist file)",
        validators=[validate_csv_file_extension],
    )
    section = Course_Section_Field(
        required=False, help_text="Choose a course and section"
    )
    create_all_students = forms.BooleanField(
        required=False, help_text="Even students without a valid username"
    )

    class Media:
        css = {"all": ("css/forms.css",)}

    def __init__(self, *args, **kwargs):
        """
        ``override_values`` can be a dictionary, which will by used
        **instead of** ``self.cleaned_data`` for any of the supplied
        keys which are optional fields.
        Consider subclassing with hidden fields or deleted fields
        when supplying overrides, e.g.,
            ``del self.fields['section']``

        Alternately, a subclass could override the various ``get_``
        methods for the optional fields.
        """
        self.override_values = kwargs.pop("override_values", {})
        self.request_user = kwargs.pop("request_user", None)
        return super(ClasslistUploadForm, self).__init__(*args, **kwargs)

    def get_clean_value(self, key):
        """
        Check for overrides, otherwise return the cleaned data.
        Returns None if the key does not exist.
        """
        if key in self.override_values:
            return self.override_values[key]
        return self.cleaned_data.get(key, None)

    def get_section(self):
        return self.get_clean_value("section")

    def get_create_all_students(self):
        return self.get_clean_value("create_all_students")

    def clean(self):
        """
        Ensure that everything will work.
        """
        # the parent clean sets self.cleaned_data, so we don't have to
        cleaned_data = super().clean()
        section = self.get_section()
        create_all_students = self.get_create_all_students()
        fileobj = self.cleaned_data.get("classlist_file", None)
        if fileobj is None:
            raise forms.ValidationError(
                "This is not a valid Aurora classlist.  Please use the original CSV file downloaded from Aurora"
            )
        try:
            update_registrations(
                fileobj,
                section,
                require_valid_login=not create_all_students,
                source="classlist",
                commit=False,
                request_user=self.request_user,
            )
        except WrongSection:
            raise forms.ValidationError("Wrong section in Aurora classlist.")
        except InvalidCSVFormat:
            raise forms.ValidationError(
                "This is not a valid Aurora classlist.  Has the file been modified?"
            )
        except AuroraException:
            raise forms.ValidationError("There was a problem processing the classlist.")

        # Reset the stream so it can be consumed again in ``save()``
        fileobj.seek(0)
        return cleaned_data

    def save(self, commit=True):
        """
        Save a valid form.
        Returns a list of invalid logins, if any (consider saving this
        in the current request session...)
        """
        section = self.get_section()
        create_all_students = self.get_create_all_students()
        fileobj = self.cleaned_data["classlist_file"]
        results = update_registrations(
            fileobj,
            section,
            return_invalid_logins=True,
            require_valid_login=not create_all_students,
            source="classlist",
            commit=commit,
            request_user=self.request_user,
        )
        return results.get("invalid_logins", [])

    save.alters_data = True


################################################################


class ClasslistNoSectionUploadForm(ClasslistUploadForm):
    def __init__(self, *args, **kwargs):
        result = super().__init__(*args, **kwargs)
        self.fields.pop("section")
        return result


################################################################


class ClasslistCreateSectionUploadForm(ClasslistNoSectionUploadForm):
    create_section = forms.BooleanField(
        required=False,
        help_text="Create the section indicated in the classlist if necessary",
    )

    def get_section(self):
        if hasattr(self, "_section"):
            return self._section
        fileobj = self.cleaned_data.get("classlist_file", None)
        if fileobj is None:
            raise forms.ValidationError(
                "This is not a valid Aurora classlist.  Please use the original CSV file downloaded from Aurora"
            )
        try:
            section_qs = read_section_queryset(
                fileobj, create=self.cleaned_data["create_section"]
            )
        except (InvalidSection, InvalidCSVFormat) as e:
            raise forms.ValidationError(str(e))
        section = section_qs.get()
        self._section = section
        return self._section


################################################################


class StudentReportUploadForm(forms.Form):
    """
    For uploading aurora student reports; i.e., to populate
    StudentRegistrations (and Students).

    You may consider subclassing this form based on your needs.
    """

    create_all_students = forms.BooleanField(
        required=False, initial=True, help_text="Even students without a valid username"
    )
    ignore_unknown_sections = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Ignore sections that cannot be matched (e.g., challenge for credit sections)",
    )
    classlist_file = forms.FileField(
        label="Report from Aurora",
        help_text="Report from Aurora (do not upload a modified report file)",
        validators=[validate_csv_file_extension],
    )

    class Media:
        css = {"all": ("css/forms.css",)}

    def clean(self):
        """
        Ensure that everything will work.
        """
        # the parent clean sets self.cleaned_data, so we don't have to
        cleaned_data = super().clean()
        create_all_students = self.cleaned_data.get("create_all_students", True)
        fileobj = self.cleaned_data.get("classlist_file", None)
        if fileobj is None:
            raise forms.ValidationError(
                "This is not a valid Aurora report.  Please use the original CSV file downloaded from Aurora"
            )
        try:
            update_registrations(
                fileobj,
                require_valid_login=not create_all_students,
                ignore_unknown_sections=self.cleaned_data.get(
                    "ignore_unknown_sections", True
                ),
                source="report",
                commit=False,
            )
        except InvalidCSVFormat:
            raise forms.ValidationError(
                "This is not a valid Aurora report.  Has the file been modified?"
            )
        except InvalidSection:
            raise forms.ValidationError(
                "There was one or more unknown sections in this report."
            )
        except AuroraException:
            raise forms.ValidationError("There was a problem processing the classlist.")

        # Reset the stream so it can be consumed again in ``save()``
        fileobj.seek(0)
        return cleaned_data

    def save(self, commit=True):
        """
        Save a valid form.
        Returns a list of invalid logins, if any (consider saving this
        in the current request session...)
        """
        create_all_students = self.cleaned_data.get("create_all_students", True)
        fileobj = self.cleaned_data["classlist_file"]
        results = update_registrations(
            fileobj,
            return_invalid_logins=True,
            require_valid_login=not create_all_students,
            ignore_unknown_sections=self.cleaned_data.get(
                "ignore_unknown_sections", True
            ),
            source="report",
            commit=commit,
        )
        return results

    save.alters_data = True


################################################################

#
