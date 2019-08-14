"""
Specify a (comma delimited) list of requirement labels 
(Default: all requirements), e.g., "honesty,i-clicker".
Use the tag "?" to get a list of available requirements.
"""
#######################
from __future__ import print_function, unicode_literals

from optparse import make_option

from classes.models import Section
from django.conf import settings
from students.models import RequirementTag, SectionRequirement

#######################
#######################################################################

#######################################################################

DJANGO_COMMAND = "main"
OPTION_LIST = (
    make_option(
        "--reqs",
        dest="reqs",
        help="Specify a (comma delimited) list of requirement labels "
        + '(Default: all requirements), e.g., "honesty,i-clicker".'
        + 'Use the tag "?" to get a list of available requirements.',
    ),
    make_option(
        "--pk",
        action="store_true",
        help="Indicates that the arguments are primary keys for sections,"
        + " not course names.",
    ),
)
HELP_TEXT = "Setup the requirements for next term's course sections."
ARGS_USAGE = "<course> [course [...]]"

#######################################################################


def do_section(section, req_tags):
    """
    Set requirements for one section.
    """
    tags = list(req_tags)
    # remove iclicker from distance sections
    if section.section_name.startswith("D") and "i-clicker" in tags:
        idx = tags.index("i-clicker")
        tags.pop(idx)

    # setup:
    section_requirements, created_flag = SectionRequirement.objects.get_or_create(
        section=section
    )
    if not created_flag:
        print("[!!!]", section, ": not modifying existing requirements")
        return  # refuse to modify existing requirements!!

    # do it!
    print(section, ":", end=" ")
    section_requirements.save()
    for label in tags:
        try:
            tag = RequirementTag.objects.get(active=True, label=label)
        except RequirementTag.DoesNotExist:
            print("[!] {0!r} is not a valid requirement tag... skipping".format(label))
        else:
            section_requirements.requirements.add(tag)
            print(label, end=" ")
    section_requirements.save()
    print


#######################################################################


def main(options, args):
    """
    Do the command!
    """
    try:
        requirements = settings.STUDENTS_REGISTRATION_REQUIREMENTS
    except AttributeError:
        raise CommandError("Add STUDENTS_REGISTRATION_REQUIREMENTS to your settings.")

    if not args:
        if options["pk"]:
            print("Error: you must supply one or more section primary keys, e.g.,")
            print("python manage.py students set_section_requirements.py --pk 100 101")
        else:
            print("Error: you must supply one or more course slugs, e.g.,")
            print(
                "python manage.py students set_section_requirements.py stat-1000 stat-2000"
            )
            print("Note that these sections will be loaded for *next* term.")

    if "reqs" not in options or not options["reqs"]:
        req_tags = [e[0] for e in requirements]
    else:
        req_tags = options["reqs"].split(",")

    if "?" in req_tags:
        print("Available requirement labels: ", ", ".join([e[0] for e in requirements]))
        return

    if options["pk"]:
        section_list = Section.objects.filter(pk__in=args)
        for section in section_list:
            do_section(section, req_tags)

    else:
        for course_name in args:
            for section in Section.objects.get_next_term(
                course__slug__iexact=course_name
            ):
                do_section(section, req_tags)


#######################################################################
