"""
Load one or more aurora classlists from the command line.
"""
import os
import pprint
import sys
from optparse import make_option

from students.utils import aurora

DJANGO_COMMAND = "main"
OPTION_LIST = (
    #         make_option('--requirement',
    #             help='Specify a requirement label ' +\
    #                  'Use the label "?" to get a list of available requirements.',
    #             ),
    #         make_option('--fail',
    #             action='store_true',
    #             default=False,
    #             help='Instead of showing students that have passed the named ' +\
    #                 'requirement, show students that have *failed*',
    #             )
)
HELP_TEXT = __doc__.strip()
ARGS_USAGE = "<filename> [filename [...]]"


def load_file(filename):
    results = aurora.update_registrations(filename, return_invalid_logins=True)
    pprint.pprint(results)


def main(options, args):
    for arg in args:
        load_file(arg)


#
