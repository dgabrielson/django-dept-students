"""
Students/i>clicker backport from lmsapp plugin.
"""
#######################################################################

from django.conf.urls import url

from .views import (
    ClickerCreateView,
    ClickerDeleteView,
    ClickerDetailView,
    ClickerListView,
    ClickerUpdateView,
)

#######################################################################

urlpatterns = [
    url(r"^$", ClickerListView.as_view(), name="students-iclicker-list"),
    url(
        r"^(?P<pk>\d+)/$", ClickerDetailView.as_view(), name="students-iclicker-detail"
    ),
    url(r"^register/$", ClickerCreateView.as_view(), name="students-iclicker-create"),
    url(
        r"^(?P<pk>\d+)/update/$",
        ClickerUpdateView.as_view(),
        name="students-iclicker-update",
    ),
    url(
        r"^(?P<pk>\d+)/delete/$",
        ClickerDeleteView.as_view(),
        name="students-iclicker-delete",
    ),
]

#######################################################################
