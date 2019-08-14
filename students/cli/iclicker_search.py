#######################
from __future__ import print_function, unicode_literals

from optparse import make_option

from ..models import iclicker as Model
from . import iclicker_detail

#######################
#######################################################################

HELP_TEXT = "Search for iclicker objects"
DJANGO_COMMAND = "main"
OPTION_LIST = (
    make_option(
        "--no-detail",
        action="store_false",
        dest="show-detail",
        default=True,
        help="By default, when only one result is returned, details will be printed also.  Giving this flag supresses this behaviour",
    ),
)
ARGS_USAGE = "[search terms]"

#######################################################################

#######################################################################


def main(options, args):
    obj_list = Model.objects.search(*args)
    if options["show-detail"] and obj_list.count() == 1:
        iclicker_detail.main(options, obj_list.values_list("pk", flat=True))
    else:
        for obj in obj_list:
            print("{}".format(obj.pk) + "\t" + "{}".format(obj))


#######################################################################
