#!/usr/bin/env python
#! -*- encoding: utf-8 -*-
"""
"""
#######################
from __future__ import print_function, unicode_literals

import csv
import os
import pprint
import random
import sys

import spreadsheet

#######################
SEATS_PER_STUDENT = 2


def get_student_count(classlist, start, finish):
    """
    [start, finish), in the python style.
    """
    count = 0
    for student_row in classlist:
        name = student_row[0].lower()
        if start <= name < finish:
            count += 1
    return count


def get_results(
    rooms, classlist, roomdict, startdict, seats_per_student=SEATS_PER_STUDENT
):

    results = []
    for room_idx in range(len(rooms)):
        if room_idx + 1 == len(rooms):
            finish = "|"  # sorts after 'z'
        else:
            finish = startdict[rooms[room_idx + 1]].lower()
        room = rooms[room_idx]
        start = startdict[room].lower()
        count = get_student_count(classlist, start, finish)
        capacity = roomdict[room]
        results.append(
            [room, capacity, count, capacity // seats_per_student - count, start]
        )
    return results


def main(
    classlist_fn, assignment_fn, seats_per_student=SEATS_PER_STUDENT, max_letters=2
):
    classlist = spreadsheet.readSheet(classlist_fn)  # list of (name, number, section)
    assignment_list = csv_load.main(
        assignment_fn
    )  # room, seat count, student count, extra, start
    roomdict = dict([(e[0], int(e[1])) for e in assignment_list])
    startdict = dict([(e[0], e[4]) for e in assignment_list])
    rooms = [e[0] for e in assignment_list]

    csv_writer = csv.writer(sys.stdout)
    for row in get_results(rooms, classlist, roomdict, startdict):
        csv_writer.writerow(row)


if __name__ == "__main__":
    classlist_filename = sys.argv[1]
    assignment_filename = sys.argv[2]
    main(classlist_filename, assignment_filename)
