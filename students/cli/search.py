"""
Find a student.
Search term can be: a student number, an iclicker ID, a UMnetID, or a name.
"""
#######################
from __future__ import print_function, unicode_literals

from optparse import make_option

from django.utils.timezone import now

from ..models import iclicker
from ..utils import find_student

#######################
###############################################################

###############################################################

DJANGO_COMMAND = "main"
OPTION_LIST = (
    make_option(
        "--current",
        action="store_true",
        help="Restrict search to current students only.",
    ),
)
ARGS_USAGE = "[search terms]"
HELP_TEXT = __doc__.strip()

###############################################################

###############################################################


def main(options, args):
    find_student.by_iclicker.use_websync = True
    arg = " ".join(args)

    dt = now() if options.get("current", False) else None
    try:
        print("Search term:", repr(arg))
        student = find_student.search(arg, current_only_dt=dt)
    except find_student.NoStudentFound:
        print("***", "no students found")
    except find_student.StudentNotUnique:
        print(
            "***",
            "more than one student found (use narrower search terms, or try --current)",
        )
    else:
        find_student.pprint(student)


###############################################################
