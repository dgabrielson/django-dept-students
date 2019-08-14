"""
This program is designed to filter out students from a class that
have been dropped in the internal FIPPA database.

When uploading results:
* Select "Mark these usernames as dropped"
and DO NOT check:
* overwrite passwords or overwrite email addresses.

After uploading, email webassign-instructors@stats.umanitoba.ca with the following:


Hi All,

I have just done the drops for failed / incomplete honesty declarations in STAT 1000 and 2000.

If your students start complaining about "not being registered in any courses" in WebAssign or the Stats Gradebook, they have most likely been dropped.

Dropped students who have valid aurora registrations have received an email like the following:
======================================
Hello {{ given_name }},

You have been dropped from WebAssign because you did not successfully complete the honesty declaration.

To get back on to WebAssign, you need to download and complete the paper honesty declaraction from http://www.stats.umanitoba.ca/media/statsweb/files/2010/10/honesty.pdf and return it to your instructor.

Course: {{ section.Course }}
Section: {{ section.Section_Name }}
Instructor: {{ section.Instructor }}
            http://www.stats.umanitoba.ca{{ section.Instructor.get_directory_href }}
======================================

After you receive a signed paper honesty declaration, please email me with the student's information and I will reinstate the student in WebAssign.

"""
#######################
from __future__ import print_function, unicode_literals

import os

from classes.models import Section
from students.models import Student_Registration

#######################


def filename(section):
    return (
        (section.Course.Short_Name + " " + section.Section_Name)
        .replace(":", "_")
        .replace(" ", "_")
        .replace("__", "_")
        .lower()
    )


def do_droplist(section):
    lines = ["username,fullname,password,email"]
    # for student in Student.objects.all().filter(Account_Created= True, Active= True, Permission_Given=True, Sections= section):
    for reg in Student_Registration.objects.filter(
        Active=True, section=section, status="CC"
    ):
        if reg.good_standing():
            student = reg.student
            line = (
                student.UMnetID
                + ',"'
                + student.Name
                + '",'
                + student.Initial_Password
                + ","
                + student.Email
            )
            lines.append(line)

    csv = "\n".join(lines)
    output_fn = filename(section) + ".csv"
    print(output_fn)
    open(output_fn, "w").write(csv.encode("utf-8", "replace"))
    if not os.path.exists(os.path.expanduser("~/tmp/")):
        os.mkdir(os.path.expanduser("~/tmp/"))
    os.rename(output_fn, os.path.expanduser("~/tmp/") + output_fn)


def main():
    sections = Section.objects.all().filter(Active=True, Using_WebAssign=True)
    for section in sections:
        do_droplist(section)


if __name__ == "__main__":
    main()

#
