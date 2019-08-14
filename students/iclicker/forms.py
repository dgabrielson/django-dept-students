"""
Students/i>clicker backport from lmsapp plugin.

i>clicker forms.
"""
#######################################################################

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.db import IntegrityError

from ..models import Student, iclicker

#######################################################################


class iClickerForm(forms.ModelForm):
    """
    i>clicker form for students.
    """

    student = forms.ModelChoiceField(
        required=False, widget=forms.HiddenInput, queryset=Student.objects.all()
    )

    class Meta:
        model = iclicker
        fields = ["student", "iclicker_id"]
        error_messages = {
            # There is only one unique_together constraint on this model,
            #   so we can provide a more user-based error message:
            NON_FIELD_ERRORS: {
                "unique_together": "You have already registered this i>clicker."
            }
        }

    class Media:
        css = {"all": ("css/forms.css",)}

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        return super().__init__(*args, **kwargs)

    def clean(self):
        student_id = self.data.get("student")
        try:
            student_id = int(self.data.get("student", None))
        except ValueError:
            raise forms.ValidationError(
                """There was a problem accessing your student information.
                Please contact your instructor.
                [i>clicker registration issue: 1]"""
            )

        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            raise forms.ValidationError(
                """There was a problem accessing your student information.
                Please contact your instructor.
                [i>clicker registration issue: 5]"""
            )
        if not student:
            raise forms.ValidationError(
                """There was a problem accessing your student information.
                Please contact your instructor.
                [i>clicker registration issue: 2]"""
            )
        if not student.active:
            raise forms.ValidationError(
                """There was a problem accessing your student information.
                Please contact your instructor.
                [i>clicker registration issue: 3]"""
            )
        if not student.person.active:
            raise forms.ValidationError(
                """There was a problem accessing your student information.
                Please contact your instructor.
                [i>clicker registration issue: 4]"""
            )

    def clean_iclicker_id(self):
        """
        Ensure a proper i>clicker ID.
        """
        iclicker_id = self.data.get("iclicker_id").lower()

        if len(iclicker_id) != 8:
            raise forms.ValidationError(
                "Your i>clicker ID is a series of 8 numbers and letters."
            )
        try:
            n = int(iclicker_id, 16)
        except ValueError:
            raise forms.ValidationError(
                "Your i>clicker ID is a series of 8 numbers and letters."
            )

        try:
            student_id = int(self.data.get("student", None))
        except ValueError:
            # fail on general form clean.
            return iclicker_id

        qs = iclicker.objects.filter(student=student_id, iclicker_id=iclicker_id)
        if qs.exists():
            raise forms.ValidationError("You have already registered this i>clicker.")

        return iclicker_id

    def save(self, commit=True):
        """
        Default save plus student logging
        """
        try:
            instance = super(iClickerForm, self).save(commit=commit)
        except IntegrityError as e:
            iclicker_id = self.data.get("iclicker_id").lower()
            student_id = self.data.get("student")
            qs = iclicker.objects.filter(student=student_id, iclicker_id=iclicker_id)
            if not qs.exists():
                raise e
            # ... registration already exists, but validation didn't catch?
            # seen in production 2018-Jan-10
            instance = qs.get()  # should only be one (database contraint)
        else:
            if commit:
                instance.student.History_Update(
                    "students.iclicker.form",
                    "student add iclicker registration " + instance.iclicker_id,
                    user=self.request_user,
                )
        return instance


#######################################################################
