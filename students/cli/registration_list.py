"""
Dump the registration list for a section.
"""
#######################
from __future__ import print_function, unicode_literals

from ..models import Student_Registration

#######################

DJANGO_COMMAND = "main"
OPTION_LIST = ()
ARGS_USAGE = "<section_pk>"
HELP_TEXT = __doc__.strip()


def main(options, args):
    """
    Dump registration list for sections named by primary keys in args.
    """
    for arg in args:
        registration_list = Student_Registration.objects.filter(section__pk=arg)
        for reg in registration_list:
            print(reg.student.student_number)
