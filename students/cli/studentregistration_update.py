"""
CLI update for Student_Registration objects
(from Aurora classlists)
"""
#######################################################################
#######################################################################
from optparse import make_option

from ..utils import aurora2 as aurora

HELP_TEXT = __doc__.strip()
DJANGO_COMMAND = "main"
OPTION_LIST = ()
ARGS_USAGE = "csv [csv [...]]"

#######################################################################

#######################################################################


def main(options, args):

    verbosity = int(options.get("verbosity"))

    for arg in args:
        with open(arg) as f:
            aurora.update_registrations(f)


#######################################################################
