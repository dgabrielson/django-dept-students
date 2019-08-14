"""
Get a report for a section or group of sections for which students
have passed or failed a given requirement.
(Only aurora verified students are reported.)
"""
#######################
from __future__ import print_function, unicode_literals

#######################
from optparse import make_option

from classes.models import Section
from django.conf import settings
from students.models import RequirementCheck, Student_Registration

DJANGO_COMMAND = "main"
OPTION_LIST = (
    make_option(
        "--requirement",
        help="Specify a requirement label "
        + 'Use the label "?" to get a list of available requirements.',
    ),
    make_option(
        "--fail",
        action="store_true",
        default=False,
        help="Instead of showing students that have passed the named "
        + "requirement, show students that have *failed*",
    ),
)
HELP_TEXT = __doc__.strip()
ARGS_USAGE = "<section_pk> [section_pk [...]]"


def main(options, args):
    """
    Do the command!
    """
    try:
        requirements = settings.STUDENTS_REGISTRATION_REQUIREMENTS
    except AttributeError:
        raise CommandError("Add STUDENTS_REGISTRATION_REQUIREMENTS to your settings.")
    requirements = [e[0] for e in requirements]

    if not args:
        print("Error: you must supply one or more section primary keys")
        return
    # allow any number of args, and each arg could be a comma delimited list:
    section_pk_set = set(",".join(args).split(","))

    if "requirement" not in options or not options["requirement"]:
        print("You must supply a requirement tag")
        return

    if "?" == options["requirement"] or options["requirement"] not in requirements:
        if options["requirement"] not in requirements:
            print("Invalid requirement: %r" % options["requirement"])
        print("Available requirement labels: ", end=" ")
        print(", ".join(requirements))
        return

    section_list = Section.objects.filter(pk__in=section_pk_set)
    reg_list = Student_Registration.objects.filter(
        section__in=section_list, aurora_verified=True
    ).order_by("section", "student")
    for reg in reg_list:
        flag = RequirementCheck.objects.is_complete(reg, options["requirement"])
        if options["fail"]:
            flag = not flag  # invert meaning
        if flag:
            print(reg.section, "\t", reg.student, "\t", reg.student.student_number)
