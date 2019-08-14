"""
Students/i>clicker backport from lmsapp plugin.

i>clicker views.
"""
#######################################################################

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

# from lms_core.views.mixins import LmsAuthMixin
from django.utils.decorators import method_decorator
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from people.models import Person

from ..models import Student, iclicker
from .forms import iClickerForm

##

#######################################################################


class LoginRequiredMixin(object):
    """
    View mixin which requires that the user is authenticated.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


#######################################################################


class LmsAuthMixin(LoginRequiredMixin):
    """
    View mixin which requires that the user is authenticated, also adds
    some auth related variables to the context.
    """

    def _set_lms_person_roles(self):
        """
        Set self.person and self.roles.
        """
        if not hasattr(self, "person"):
            try:
                self.person = Person.objects.get_by_user(self.request.user)
            except Person.DoesNotExist:
                self.person = None

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with the person and their roles.
        """
        context = super(LmsAuthMixin, self).get_context_data(*args, **kwargs)
        self._set_lms_person_roles()
        context["person"] = self.person
        return context


#######################################################################


class ClickerBaseMixin(LmsAuthMixin):
    """
    Core i>clicker mixin.
    """

    form_class = iClickerForm
    queryset = iclicker.objects.filter(active=True)
    success_url = reverse_lazy("students-iclicker-list")

    def _set_lms_person_roles(self, *args, **kwargs):
        """
        Include student information.
        """
        result = super()._set_lms_person_roles(*args, **kwargs)
        try:
            self.student = self.person.student
        except Student.DoesNotExist:
            self.student = None
        return result

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = getattr(self.request, "user", None)
        return kwargs

    def get_queryset(self, *args, **kwargs):
        """
        Restrict the queryset to roles for the current person.
        """
        queryset = super().get_queryset(*args, **kwargs)
        self._set_lms_person_roles()
        if self.student is None:
            return queryset.none()
        else:
            return queryset.filter(student=self.student)

    def get_initial(self, *args, **kwargs):
        """
        Provide the student as initial data.
        """
        self._set_lms_person_roles()
        initial = super().get_initial(*args, **kwargs)
        initial["student"] = self.student
        return initial

    def get_context_data(self, *args, **kwargs):
        """
        Augument the context with the student information.
        """
        self._set_lms_person_roles()
        context = super().get_context_data(*args, **kwargs)
        context["student"] = self.student
        return context


#######################################################################


class ClickerListView(ClickerBaseMixin, ListView):
    """
    List clickers.
    """


#######################################################################


class ClickerDetailView(ClickerBaseMixin, DetailView):
    """
    Detail for a single clicker.
    """


#######################################################################


class ClickerCreateView(ClickerBaseMixin, CreateView):
    """
    Create a single clicker.
    """

    template_name = "students/iclicker_create.html"


#######################################################################


class ClickerUpdateView(ClickerBaseMixin, UpdateView):
    """
    Update a single clicker.
    """

    template_name = "students/iclicker_update.html"


#######################################################################


class ClickerDeleteView(ClickerBaseMixin, DeleteView):
    """
    Delete a single clicker.
    """

    def delete(self, *args, **kwargs):
        """
        Don't actually delete -- just deactivate.
        """
        self.object = self.get_object()
        self.object.student.History_Update(
            "students.iclicker.delete",
            "student deleted their iclicker " + self.object.iclicker_id,
            user=getattr(self.request, "user", None),
        )
        return super(ClickerDeleteView, self).delete(*args, **kwargs)


#######################################################################
