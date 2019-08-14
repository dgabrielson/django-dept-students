# Source: https://medium.com/@hakibenita/things-you-must-know-about-django-admin-as-your-app-gets-bigger-6be0b0ee9614#.afaow5k2t
#######################
from __future__ import print_function, unicode_literals

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import six

#######################

if six.PY3:
    from urllib.parse import urlencode
if six.PY2:
    from urllib import urlencode


class DefaultFilterMixin(object):
    """
    Override to implement::
    
    def get_default_filters(self, request):
        now = timezone.now()
        return {
            'created__year': now.year,
            'created__month': now.month,
        }
    """

    def get_default_filters(self, request):
        """Set default filters to the page.
            request (Request)
            Returns (dict):
                Default filter to encode.
        """
        raise NotImplementedError()

    def changelist_view(self, request, extra_context=None):
        ref = request.META.get("HTTP_REFERER", "")
        if "?" in ref:
            ref = ref.split("?", 1)[0]
        # Use reverse() [instead of ``request.META.get('PATH_INFO', '')``
        #   so that SCRIPT_NAME is handled.
        info = self.model._meta.app_label, self.model._meta.model_name
        path = reverse("%s:%s_%s_changelist" % ((self.admin_site.name,) + info))
        # If already have query parameters or if the page
        # was referred from it self (by drilldown or redirect)
        # don't apply default filter.
        default_filters = self.get_default_filters(request)
        if default_filters is None or len(request.GET.keys()) > 0 or ref.endswith(path):
            return super(DefaultFilterMixin, self).changelist_view(
                request, extra_context=extra_context
            )
        query = urlencode(default_filters)
        return redirect("{}?{}".format(path, query))
