#######################
from __future__ import print_function, unicode_literals

import sys
from datetime import datetime, timedelta

from classes import conf
from classes.models import Semester

from ..models import Student, iclicker

#######################
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
find_student.py

Routines for finding a student.

by_iclicker(iclicker_id)

search(term)    - term can be: a student number, an iclicker ID, a UMnetID, or a name.

TODO: Make i>clicker results deal with full student numbers, i.e.,
22212-0-7673816-5
or with UMnetIDs, i.e., "umgabri0".
"""
################################################################

# import urllib2
# Python 2 and 3:
try:
    # Python 3:
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    # Python 2:
    from urllib2 import urlopen, HTTPError, URLError

################################################################


class StudentNotUnique(Exception):
    pass


################################################################


class NoStudentFound(Exception):
    pass


################################################################


def __iclicker_websync(iclicker_id):
    while len(iclicker_id) < 8:  # MAJICK NUMBER!
        iclicker_id = "0" + iclicker_id
    # print( 'checking for websync with id', iclicker_id)
    url = (
        "http://www.iclicker.com/iclickerregistration/GetRegistered.aspx?c="
        + iclicker_id
    )
    fp = urlopen(url)
    text = fp.read().replace("\r\n", "\n")
    fp.close()
    if text.find("\n\n\n") != -1:
        rows, html = text.split("\n\n\n", 1)
        data = [row.split("\t") for row in rows.split("\n")]
        saved = False
        for row in data:
            found = False
            # row = ['1', '1BCE01D4', 'Dave', 'Gabrielson', '6713309', '11/16/2009 5:24:15 PM', ' ']
            try:
                try:
                    n = int(row[4])  # students registering with their UMnetID
                except ValueError:
                    pass
                try:
                    # students put strange things here... can cause problems.
                    number = int(row[4])
                except ValueError:
                    number = -1
                student = Student.objects.get(active=True, student_number=number)
            except Student.DoesNotExist:
                pass
            else:
                found = True

            if not found:
                continue

            # verify that the student has a current registration also!
            if not student.student_registration_set.reg_list(
                good_standing=True
            ).exists():
                continue

            # check to see if this mapping exists
            try:
                mapping = iclicker.objects.get(iclicker_id=iclicker_id, student=student)
            except iclicker.DoesNotExist:  # new mapping
                mapping = iclicker(iclicker_id=iclicker_id, student=student)
                student.History_Update(
                    "iclicker.websync",
                    "found new www.iclicker.com web registration for iclicker ID "
                    + iclicker_id,
                )
            if not mapping.active:  # reactivate
                mapping.active = True
                student.History_Update(
                    "iclicker.websync",
                    "reactivated www.iclicker.com web registration for iclicker ID "
                    + iclicker_id,
                )

            mapping.save()
            student.save()
            saved = True

        if saved:
            return by_iclicker(iclicker_id)  # recursion alert!

    raise NoStudentFound


################################################################


def by_iclicker(iclicker_id):
    """
    set the function attribute by_iclicker.use_websync = True, to use WebSync lookups
    """
    if not hasattr(by_iclicker, "use_websync"):
        by_iclicker.use_websync = False

    map_results = iclicker.objects.filter(active=True, iclicker_id__iexact=iclicker_id)
    if len(map_results) == 1:
        return map_results[0].student
    elif len(map_results) > 1:
        raise StudentNotUnique
    elif by_iclicker.use_websync:
        try:
            return __iclicker_websync(iclicker_id)  # recursion alert!
        except URLError:
            print(
                "Error doing www.iclicker.com websync. ID:",
                iclicker_id,
                file=sys.stderr,
            )
    raise NoStudentFound


################################################################


def isnumeric(s):
    for c in s:
        if c not in "0123456789":
            return False
    return True


################################################################


def ishexnumeric(s):
    for c in s.lower():
        if c not in "0123456789abcdef":
            return False
    return True


################################################################


def pprint(student):
    print("            pk\t{0}".format(student.pk))
    print("      username\t{0}".format(student.person.username))
    print("          name\t{0}".format(student.person.cn))
    print("student number\t{0}".format(student.student_number))
    for email in student.person.emailaddress_set.all():
        print("         email\t{0}".format(email), end=" ")
        if email.preferred:
            print("\t[preferred]", end=" ")
        if not email.active:
            print("\t[DO NOT USE]", end=" ")
        print()
    for phone in student.person.phonenumber_set.all():
        print("         phone\t{0}".format(phone), end=" ")
        if phone.preferred:
            print("\t[preferred]", end=" ")
        if not phone.active:
            print("\t[DO NOT USE]", end=" ")
        print
    for iclicker_map in iclicker.objects.filter(active=True, student=student):
        print("     i>clicker\t{0}".format(iclicker_map.iclicker_id))
    print("       active\t{0}".format(student.active))
    print("last modified\t{0}".format(student.modified))
    print()
    print(":REGISTRATIONS:")
    for reg in student.get_registrations():
        print("\t", reg.pk, "\t", reg.section, ":", reg.get_status_display())
    if student.person.note:
        print()
        print(":NOTES:")
        print(student.person.note)
    if student.history:
        print()
        print(":HISTORY:")
        print(student.history)
    print()


################################################################


def search(term, current_only_dt=None):
    results = None
    if len(term) in [6, 7] and isnumeric(term):
        # student number
        results = Student.objects.filter(active=True, student_number=term)
    elif len(term) <= 8:
        if ishexnumeric(term):
            # iclicker ID
            return by_iclicker(term)
        else:
            # umnetid
            results = Student.objects.filter(active=True, person__username=term)
    if not results:
        # name
        terms = term.replace(",", "").split()
        results = Student.objects.filter(active=True)
        for fragment in terms:
            results = results.filter(person__cn__icontains=fragment)

    if current_only_dt is not None:
        rules = conf.get("semester:advertisement_rules")
        if isinstance(current_only_dt, datetime):
            current_only_dt = current_only_dt.date()
        semester = Semester.objects.get_by_date(current_only_dt)
        delta = timedelta(days=rules["grace_period"].get(semester.term, 0))
        results = results.filter(
            student_registration__section__sectionschedule__date_range__start__lte=current_only_dt,
            student_registration__section__sectionschedule__date_range__finish__gte=current_only_dt
            - delta,
            active=True,
            student_registration__active=True,
            student_registration__section__active=True,
            student_registration__section__sectionschedule__active=True,
            student_registration__section__sectionschedule__date_range__active=True,
        )

    if len(results) == 0:
        raise NoStudentFound
    if len(results) == 1:
        return results.get()
    if len(results) > 1:
        raise StudentNotUnique


################################################################

if __name__ == "__main__":
    import sys

    by_iclicker.use_websync = True
    for arg in sys.argv[1:]:
        try:
            print("Search term:", repr(arg))
            student = search(arg)
        except NoStudentFound:
            print("***", "no students found")
        except StudentNotUnique:
            print("***", "more than one student found (use narrower search terms)")
        else:
            pprint(student)

################################################################
#
