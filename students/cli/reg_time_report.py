"""
Registration interval report.
Return info on repeat registration 12 months or more apart.
"""
#######################
from __future__ import print_function, unicode_literals

import time

from classes.models import Semester
from students.models import Student, Student_Registration

#######################

DJANGO_COMMAND = "main"
OPTION_LIST = ()
# ARGS_USAGE = '[search terms]'
HELP_TEXT = __doc__

coursename_list = ["STAT 1000", "STAT 2000"]


def term_index_semester(term):
    y = term.Year
    m = int(term.Term[0])
    return 12 * y + m - 1


def term_index(registration):
    """
    Return the corresponding term index for this registration.
    """
    return term_index_semester(registration.section.Term)


def term_sequence(student):  # T(s)
    """
    Generate the term sequence for the given student:
        t = 12y + m - 1 for each registration of this student
    """
    terms = [
        term_index(r)
        for r in student.student_registration_set.filter(
            section__Course__Short_Name__in=coursename_list
        )
    ]
    terms = list(set(terms))  # remove duplicates
    terms.sort()
    return terms


def month_delta(T, t):  # \delta(T(s), t_i)
    """
    T is a term sequence for a student
    t is a term index
    """
    if t not in T:
        return 0
    t0 = T[0]
    return t - t0


def check(T, t, threshold=12):  # a(T(s), t)
    """
    T is a term sequence for a student
    t is a term index
    """
    return int(month_delta(T, t) >= threshold)


def main(options, args):
    sequence_list = []

    threshold = 12

    tick = time.time()
    # this will probably take a while...
    for student in Student.objects.all().select_related():
        sequence_list.append(term_sequence(student))
    tock = time.time()
    print(
        "**",
        "sequence list generation complete. Elapsed time is %.1f sec" % (tock - tick),
    )

    for term in Semester.objects.all():
        t = term_index_semester(term)
        A_t = [check(T, t, threshold) for T in sequence_list]
        M_t = sum(A_t)
        if M_t != 0:
            N_t = Student_Registration.objects.filter(
                section__Course__Short_Name__in=coursename_list, section__Term=term
            ).count()
            P_t = float(M_t) / N_t
            print(term, "\t", M_t, "\t", N_t, "\t", P_t)


#
