"""
Get old / current student registrations, low level.

python list_student_regs.py student_number 
"""
#######################
from __future__ import print_function, unicode_literals

from students.models import Student_Registration

#######################


def main(student_number):
    regs = Student_Registration.objects.filter(
        student__Student_Number=student_number
    ).order_by("section")
    try:
        print("Student:\t%s [%s]" % (regs[0].student, student_number))
    except IndexError:
        print("No registration records for this student")
        return

    for r in regs:
        print(
            "{}".format(r.section.id)
            + "\t"
            + "{}".format(r.section)
            + "\t"
            + "{}".format(r.section.Term)
        )


if __name__ == "__main__":
    import sys

    student_number = sys.argv[1]
    main(student_number)
#
