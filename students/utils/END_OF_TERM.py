#!/usr/bin/env python
# -*- coding: utf-8 -*-

from students.models import Student, Student_Registration, iclicker


def main():
    #     for student in Student.objects.filter(active=True):
    #         student.active = False
    #         student.History_Update( 'disable_old_students', 'student deactivated (end of term)')
    #         student.save()

    #     for reg in Student_Registration.objects.exclude(status='00'):
    #         reg.active = False
    #         reg.status = '00'
    #         reg.save()
    Student_Registration.objects.exclude(status="00").update(active=False, status="00")

    #     for iclicker_registration in iclicker.objects.filter(active=True):
    #         iclicker_registration.active = False
    #         iclicker_registration.save()
    iclicker.objects.filter(active=True).update(active=False)


#
