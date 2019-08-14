#######################
from __future__ import print_function, unicode_literals

from ..models import iclicker as Model
from . import object_detail

#######################
#######################################################################

HELP_TEXT = "Deactivate an i>clicker registration"
DJANGO_COMMAND = "main"
OPTION_LIST = ()
ARGS_USAGE = "iclicker_id [iclicker_id [...]]"

#######################################################################

M2M_FIELDS = []
RELATED_ONLY = []  # Specify a list or None; None means introspect for related
RELATED_EXCLUDE = []  # any related fields to skip

#######################################################################


def main(options, args):
    for arg in args:
        # get the object
        obj = Model.objects.get(iclicker_id=arg)
        if obj.active:
            obj.active = False
            obj.save()
        print(object_detail(obj, M2M_FIELDS, RELATED_ONLY, RELATED_EXCLUDE))


#######################################################################
