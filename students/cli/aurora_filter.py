"""
This program is designed to filter out students from a class that
are not registered in that class in aurora.

INPUT:  An aurora class list.

Typical usage:
    python aurora_filter.py ~/Desktop/Aurora\ Checks\ {1,2}000/*.csv

Run aurora_filter.py.
Then run honesty_filter.py
Then run drop_lists.py
"""
#######################
from __future__ import print_function, unicode_literals

import csv

#######################
import sys

from django.template import Context, Template
from students.models import Section, Student, Student_Registration
from students.utils import aurora


def get_given_name(student):
    if "," in student.Name:
        return student.Name.split(",")[-1].strip()
    return student.Name.split()[0]


# BODY_TEMPLATE = '''Hello {{ given_name }},
#
# You have been dropped from WebAssign becuase you are either no longer registered in this course or because you are not registered in this section.
#
# To get back on to WebAssign, you need to reply to this email with your correct course and section (as it appears in Aurora).
#
# Your current WebAssign section is: {{ section }}.
#'''

BODY_TEMPLATE = """Hello {{ given_name }},

You have been de-registered from WebAssign because the student number you entered in the WebAssign signup form ({{ student_number }}) does not appear on the class list for your WebAssign section: {{ section }}.

To get back on to WebAssign, you need to reply to this email with your correct course and section (as it appears in Aurora), or your correct student number (if you are in the correct section).
"""


def send_email(student, section):
    return
    # don't do anything any more... registering for the wrong class is now hard.


#     body_tmpl = BODY_TEMPLATE
#
#     t = Template(body_tmpl)
#     c = Context({
#             'given_name' : get_given_name(student),
#             'section' : section,
#             'student_number' : student.Student_Number,
#         })
#     body = t.render(c)
#
#     to = student.Email
#     subject = 'WebAssign: You have been dropped'
#     mymail.main(to, subject, body)


def main(input_filename):
    section = aurora.update_registrations(input_filename)["section"]
    print(section)
    print()

    R = len(Student_Registration.objects.filter(Active=True, section=section))
    D = len(
        Student_Registration.objects.filter(
            Active=True, section=section, aurora_verified=False
        )
    )

    assert R  # going to drop everybody! bail!
    print()
    print(D, "/", R, "students have been invalidated")
    print()


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        main(arg)
    if not sys.argv[1:]:
        print(__doc__)

#
