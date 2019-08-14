"""
This module has utilities for interfacing with Aurora,
currently only aurora CSV spreadsheets.
"""
################################################################
from __future__ import print_function, unicode_literals

import datetime
import random
import re
from io import StringIO
from pprint import pprint

from classes.models import Course, Section, Semester
from django.db import IntegrityError
from django.template.defaultfilters import slugify
from django.utils.encoding import force_text
from people.models import EmailAddress, Person
from spreadsheet import SUPPORTED_FORMATS, sheetReader

from .. import conf, utils
from ..models import History, Student, Student_Registration

################################################################

NAME_PATTERN = re.compile(r"(.*), (.*)")
NAMEP_PATTERN = re.compile(r"(.*), (.*) \((.*)\)")

################################################################


class AuroraException(Exception):
    pass


class WrongSection(AuroraException):
    pass


class InvalidSection(AuroraException):
    pass


class InvalidCSVFormat(AuroraException):
    pass


class InvalidUsername(AuroraException):
    """
    Raised when valid usernames are required.
    """

    def __init__(self, student_number, name, *args, **kwargs):
        self.student_number = student_number
        self.name = name
        if not args:
            args = [
                "Skipped creating student {self.name} [{self.student_number}] -- no username.".format(
                    self=self
                )
            ]
        return super(InvalidUsername, self).__init__(*args, **kwargs)


################################################################


def process_student_row(headers, record):
    """
    Convert record into a dictionary, for more semantic access.
    Fields we might care about are:
         'Email': 'nobody@example.com',
         'Grade Mode/AutoGrade': 'VW',  # or 'AW', perhaps 'CW'
         'ID': '6713309',  # student number!
         'Student Name': 'Doe, John',
         'Telephone': '204 555-1234'

    """
    D = dict(zip(headers, [r.strip() for r in record]))
    D["ID"] = D["ID"].lstrip("0")  # fix student numbers
    # compatibilty - so that reports look a bit more like classlists
    if "Email" not in headers and "UM_EMAIL" in headers:
        D["Email"] = D["UM_EMAIL"]
    if "Student Name" not in headers and "NAME" in headers:
        D["Student Name"] = D["NAME"]
    return D


################################################################


def _get_data(fileobj):
    """
    From a fileobj, return the data or raise InvalidCSVFormat
    """
    try:
        contents = force_text(fileobj.read())
    except UnicodeDecodeError:
        raise InvalidCSVFormat("This is not a readable CSV file.")
    if not contents:
        raise InvalidCSVFormat("There is no data here.")
    fp = StringIO(contents)
    try:
        data = sheetReader(fileobj.name, fileobj=fp)
    except:
        raise InvalidCSVFormat("There was a problem reading the spreadsheet")
    if not data or not len(data) > 1:
        raise InvalidCSVFormat("This does not seem to be an aurora classlist.")
    return data


################################################################


def _extract_section_info_from_classlist_data(data):
    info = {k.lower(): data[1][i] for i, k in enumerate(data[0]) if k}
    if "course" in info and "-" in info["course"]:
        # course - section
        course, section = (e.strip() for e in info["course"].split("-", 1))
        info["course"] = course
        info["section"] = section
    return info


################################################################


def get_section_qs_from_classlist(data, create=False, dne_error=True):
    info = _extract_section_info_from_classlist_data(data)
    # print(info)
    for key in ["course", "section", "duration", "crn"]:
        if key not in info:
            raise InvalidCSVFormat(
                "This does not seem to be an aurora classlist.  Has it been altered?"
            )
    try:
        course = Course.objects.get_by_slug(info["course"].lower().replace(" ", "-"))
    except Course.DoesNotExist:
        raise InvalidSection(
            "Could not find the course for this classlist. The course {} may need to be added locally.".format(
                info["course"]
            )
        )
    start_date_str = info["duration"].split("-", 1)[0].strip()
    start_date = datetime.datetime.strptime(start_date_str, "%b %d, %Y").date()
    term = Semester.objects.get_by_date(start_date)
    search = {
        "course": course,
        "term": term,
        "section_name": info["section"],
        "crn": info["crn"],
    }
    if create:
        slug = slugify(course.slug + " " + info["section"] + " " + term.slug)
        section, flag = Section.objects.get_or_create(
            **search, defaults={"active": True, "slug": slug}
        )
        if not section.active:
            section.active = True
            section.save()
        section_qs = Section.objects.filter(pk__in=[section.pk])
    else:
        search["active"] = True
        section_qs = Section.objects.filter(**search)
    if dne_error and not section_qs.exists():
        raise InvalidSection("The section does not exist")
    return section_qs


################################################################


def read_section_queryset(fileobj, create=False, dne_error=True):
    """
    Read the classlist object and return the raw data for the
    section information.
    This method will rewind the file obj before returning.
    """
    try:
        data = _get_data(fileobj)
        return get_section_qs_from_classlist(data, create=create, dne_error=dne_error)
    finally:
        fileobj.seek(0)


################################################################


def read_classlist(fileobj):
    """
    Read the classlist, find the associated section object.
    Return the section in this classlist and the student data rows.
    """
    data = _get_data(fileobj)
    section_qs = get_section_qs_from_classlist(data, create=False)

    at_students = False
    found_students = False
    student_list = []
    for record in data:
        if record[0].startswith("NOTE: "):
            at_student = False

        if at_students:  # sometimes things can be 12, sometimes 13.
            # student records have a Record Number as the first entry
            try:
                n = int(record[0])
            except ValueError:
                pass
            else:
                student_list.append(process_student_row(headers, record))

        if record[0] == "Record Number":
            at_students = True
            found_students = True
            headers = [r.strip() for r in record]
            if "ID" not in headers:
                raise InvalidCSVFormat("Unknown Header set: 'ID' field not found")

    if not found_students:
        raise InvalidCSVFormat("No student records")

    return section_qs, student_list


################################################################


def read_report(fileobj):
    """
    Read the report, find the associated section objects.
    Return the sections in this classlist and the student data rows.
    """
    try:
        contents = force_text(fileobj.read())
    except UnicodeDecodeError:
        raise InvalidCSVFormat("This is not a readable CSV file.")
    if not contents:
        raise InvalidCSVFormat("There is no data here.")
    fp = StringIO(contents)
    try:
        data = sheetReader(fileobj.name, fileobj=fp)
    except:
        raise InvalidCSVFormat("There was a problem reading the spreadsheet")
    if not data or not len(data) > 1:
        raise InvalidCSVFormat("This does not seem to be an aurora classlist.")

    headers = data[0]
    # check for a minimal required header set.
    for h in [
        "ID",
        "NAME",
        "SUBJECT",
        "COURSE_NUMBER",
        "COURSE_SECTION_NUMBER",
        "COURSE_REFERENCE_NUMBER",
        "UM_EMAIL",
    ]:
        if h not in headers:
            raise InvalidCSVFormat(
                "This does not seem to be an aurora report. (Missing header: {})".format(
                    h
                )
            )
    # NOTE: reports have some better name information in the fields:
    #   MAILING_NAME_FORMAL, MAILING_NAME_INFORMAL, MAILING_NAME_PREFERRED
    crn_col = headers.index("COURSE_REFERENCE_NUMBER")
    crn_set = set((row[crn_col] for row in data[1:]))
    try:
        section_qs = Section.objects.filter(crn__in=crn_set, active=True)
    except Section.DoesNotExist:
        section_qs = None

    student_list = []
    for record in data[1:]:
        # student records have a Record Number as the first entry
        try:
            n = int(record[0])
        except ValueError:
            pass
        else:
            student_list.append(process_student_row(headers, record))

    return section_qs, student_list


################################################################


def _history_bulk_create(student_list, message, annotation="aurora_filter"):
    """
    For every student in the list, create the corresponding history item.
    """

    def _history(s):
        return History(student_id=s, annotation=annotation, message=message)

    history_list = [_history(s) for s in student_list]
    return History.objects.bulk_create(history_list)


################################################################


def _get_username(email):
    """
    Extract usernames from email addresses.
    NB: going forward, user@myumanitoba.ca *may* be username!
    """
    f = conf.get("aurora:student_username")
    if f is not None:
        return f(email)
    return None


################################################################


def get_or_create_student(rec, section, require_valid_login, request_user):
    """
    section is only for information purposes.

    This function now [2012-Sep-24] uses None as the invalid
    username.  Previously, '!' + stuff was used.

    This function is broken up into several subfunctions, so
    that each part is easier to understand.

    If ``require_valid_login`` is ``True``, then only valid logins
    will get created.  Student with invalid usernames will raise
    ``InvalidUsername`` exception
    """
    # Check to see if it's possible to have valid usernames...
    if conf.get("aurora:student_username") is None:
        require_valid_login = False

    def _get_core_info(rec):
        try:
            st_num = int(rec["ID"])
            email = rec["Email"]
            name = rec["Student Name"]
        except ValueError:
            raise InvalidCSVError(
                "invalid student number in Record Number %s" % rec["Record Number"]
            )
        return st_num, email, name

    def _get_or_create_student(st_num, name, username, email, require_username):
        def _get_or_create_person(name, username, email):
            def _add_email(person, created, email):
                if email is not None and email.strip() and "@" in email:
                    type_slug = conf.get("aurora:email_type_slug")(email)
                    if created:
                        person.add_email(email, type_slug, preferred=True)
                    else:
                        person.add_email(email, type_slug)

            def _add_student_flag(person):
                person.add_flag_by_name("student")

            def _update_person_names(person, sn, given_name, cn):
                """
                This will generally not be required, however since the
                class list is considere authoritative, we do anyhow.
                """
                save_person = False
                if person.sn != sn:
                    person.sn = sn
                    save_person = True
                if person.given_name != given_name:
                    person.given_name = given_name
                    save_person = True
                if person.cn != cn:
                    person.cn = cn
                    save_person = True
                if person.active != True:
                    person.active = True
                    save_person = True
                if save_person:
                    person.save()

            ### _get_or_create_person() begins
            name = "{}".format(name)
            m = NAMEP_PATTERN.match(name)
            nickname = None
            if m is not None:
                # last, first (called)
                sn, given_name, nickname = m.groups()
            else:
                m = NAME_PATTERN.search(name)
                if m is not None:
                    # last, first
                    sn, given_name = m.groups()
                    # or maybe last, first m.
                    nickname = given_name.split()[0]
                elif " " not in name:
                    # one name only
                    sn = name
                    given_name = ""
                    nickname = ""
                else:
                    # last ditch effort; no comma handling.
                    # this one is rather north-american/european specific
                    parts = name.split()
                    sn = parts[-1]
                    given_name = " ".join(parts[:-1])
                    nickname = parts[0]

            cn = given_name + " " + sn
            cn = cn.strip()
            name_dict = {"sn": sn, "given_name": nickname, "cn": cn}
            if username is not None:
                person, created = Person.objects.get_or_create(
                    username=username, defaults=name_dict
                )
            else:
                person = None
                if email:
                    try:
                        person = Person.objects.get_by_email(email)
                    except EmailAddress.DoesNotExist:
                        pass
                    else:
                        created = False
                if person is None:
                    # If all we have is a name (or a non-matching email),
                    # create a new record
                    # There could easily be more than one 'Bob Smith'
                    person = Person.objects.create(**name_dict)
                    created = True
            if created == False:
                try:
                    st = person.student
                except Student.DoesNotExist:
                    pass
                else:
                    if st.student_number != st_num:
                        # This person already belongs to a different student record.
                        #   Create a new one.
                        person = Person.objects.create(**name_dict)
                        created = True
            else:
                # can't user student.History_Update b/c not student yet!
                utils.admin_history(
                    person,
                    "Created for student #{} [/aurora2.get_or_create_student]".format(
                        st_num
                    ),
                    None,
                    request_user,
                )
            _add_student_flag(person)
            _add_email(
                person, created, email
            )  # TODO: check if this checks for preexisting.
            _update_person_names(person, sn, given_name, cn)
            return person

        ### _get_or_create_student() begins
        try:
            # this is an aurora spreadsheet, so the st_num is authoritive.
            return Student.objects.select_related("person").get(student_number=st_num)
        except Student.DoesNotExist:
            # now try lookup by username, if valid
            if username is not None:
                try:
                    return Student.objects.select_related("person").get(
                        person__username=username
                    )
                    ### NOTE: This case indicates that, although a student
                    ### record exists, it does not have a valid student
                    ### number.
                    ### This can occur with student self-registration.
                except Student.DoesNotExist:
                    pass
            elif require_username:
                raise InvalidUsername(st_num, name)

        # If no existing student is found, we're here.
        person = _get_or_create_person(name, username, email)
        try:
            student = Student.objects.create(person=person, student_number=st_num)
        except IntegrityError as e:
            qs = Student.objects.filter(student_number=st_num)
            if qs.exists():
                student = qs.get()
                student.History_Update(
                    "aurora2.get_or_create_student",
                    "Duplicate student would have been created.",
                    user=request_user,
                )
                if not student.active:
                    student.active = True
                    student.History_Update(
                        "aurora2.get_or_create_student",
                        "Reactivated student",
                        user=request_user,
                    )
                if person.pk != student.person_id:
                    student.History_Update(
                        "aurora2.get_or_create_student",
                        "WARNING: different person records detected [old: {}; new: {}] updating".format(
                            student.person_id, person.pk
                        ),
                        user=request_user,
                    )
                    student.person_id = person.pk
                if not student.person.active:
                    student.History_Update(
                        "aurora2.get_or_create_student",
                        "Reactivating person record",
                        subobj=student.person,
                        user=request_user,
                    )
                    student.person.active = True
                    student.person.save()
            else:
                raise e
        else:
            student.History_Update(
                "aurora2.get_or_create_student",
                "Created new student record for course "
                + "{} ({})".format(section, section.term),
                user=request_user,
            )
        student.save()
        return student

    def _correct_student_number(student, st_num):
        old_st_num = student.student_number
        student.student_number = st_num
        student.History_Update(
            "aurora2.get_or_create_student",
            "Correcting bad student number [was: %d], now: %d" % (old_st_num, st_num),
            user=request_user,
        )
        student.save()

    def _reactivate_student(student):
        student.active = True
        student.History_Update(
            "aurora2.get_or_create_student",
            "Reactivating student for course "
            + "{} ({})".format(section, section.term),
            user=request_user,
        )
        student.save()

    def _correct_student_username(student, username):
        # first, check to see if the correct username exists
        try:
            person = Person.objects.get(username=username)
        except Person.DoesNotExist:
            # Otherwise, change the person's username.
            old_username = student.person.username
            student.person.username = username
            student.person.save()
            student.History_Update(
                "aurora2.get_or_create_student",
                "Updating student to aurora valid username (%s --> %s)"
                % (old_username, username),
                subobj=student.person,
                user=request_user,
            )
        else:
            # Person already exists, update student to the new person record
            old_person_id = student.person_id
            student.person = person
            student.save()

            student.History_Update(
                "aurora2.get_or_create_student",
                "Updating student person record to existing person (%s --> %s)"
                % (old_person_id, person.pk),
                subobj=student.person,
                user=request_user,
            )
            # Ensure that the person record has all the correct things...
            person.add_flag_by_name("student")
            if not person.active:
                student.History_Update(
                    "aurora2.get_or_create_student",
                    "Reactivate person record",
                    subobj=student.person,
                    user=request_user,
                )
                person.active = True
                person.save()

    ### Actual function, get_or_create_student() begins ###
    debug = False
    st_num, email, name = _get_core_info(rec)
    # if st_num == 7877845:
    #     debug = True
    if debug:
        print("st_num = {0!r}".format(st_num))
        print("email = {0!r}".format(email))
        print("name = {0!r}".format(name))
    username = _get_username(email)
    if debug:
        print("username = {0!r}".format(username))
    student = _get_or_create_student(st_num, name, username, email, require_valid_login)
    if debug:
        print("student = {0!r}".format(student))

    # bad student number: assume aurora is correct.
    if st_num != student.student_number:
        if debug:
            print("_correct_student_number()")
        _correct_student_number(student, st_num)

    if not student.active:
        if debug:
            print("_reactivate_student()")
        _reactivate_student(student)

    if (
        student.person.username is None or student.person.username[0] == "!"
    ) and student.person.username != username:
        if debug:
            print("_correct_student_username()")
        _correct_student_username(student, username)

    return student


################################################################


def update_or_create_registration(
    section, student, status, require_valid_login, request_user
):
    try:
        reg = Student_Registration.objects.select_related(
            "student", "student__person"
        ).get(student=student, section=section)
        # do not clobber existing registration status
    except Student_Registration.DoesNotExist:
        reg = Student_Registration(student=student, section=section, status=status)
        reg.save()
        student.History_Update(
            "aurora2.update_or_create_registration",
            "Created student registration for course {} ({})".format(
                section, section.term
            ),
            subobj=reg,
            user=request_user,
        )
    reg.aurora_verified = True
    if status.endswith("W"):  # update any W status (withdrawl)
        reg.status = status
        student.History_Update(
            "aurora2.update_or_create_registration",
            "Student has withdrawn from course {} ({})".format(section, section.term),
            subobj=reg,
            user=request_user,
        )
    if require_valid_login and student.person.username:
        reg.save()
    elif not require_valid_login:
        reg.save()
    return reg


################################################################


def _get_report_section(rec, section_qs, cache):
    """
    This only gets called when ``source == 'report'``
    relevant record keys:
     'SUBJECT',
     'COURSE_NUMBER',
     'COURSE_SECTION_NUMBER',
     'COURSE_REFERENCE_NUMBER'
    """
    crn = rec["COURSE_REFERENCE_NUMBER"]
    if crn in cache:
        return cache[crn]

    def _get_banner_term_queryterms(academic_period):
        year = int(academic_period[:4])
        start_m = academic_period[4]
        zero = academic_period[5]
        if zero != "0":
            raise RuntimeError('invalid academic period "{}"'.format(academic_period))
        if start_m not in ["1", "5", "9"]:
            raise RuntimeError('invalid academic period "{}"'.format(academic_period))
        term = None
        if start_m == "1":
            term = "1"
        if start_m == "5":
            term = "2"
        if start_m == "9":
            term = "3"
        return {"term__year": year, "term__term": term}

    dept = rec["SUBJECT"]
    course = rec["COURSE_NUMBER"]
    section_name = rec["COURSE_SECTION_NUMBER"]

    term = _get_banner_term_queryterms(rec["ACADEMIC_PERIOD"])
    qs = section_qs.filter(
        course__department__code__iexact=dept,
        course__code__iexact=course,
        section_name__iexact=section_name,
        crn__iexact=crn,
        **term
    )

    if qs.count() == 1:
        section = qs.get()
    else:
        section = None
    cache[crn] = section
    return section


################################################################


def _get_status(rec):
    """
    Given an individual student record as returned by ``read_classlist``,
    return a registration status code.
    """
    if "Grade Mode/AutoGrade" in rec:
        # source == 'classlist'
        a_status = rec["Grade Mode/AutoGrade"].lower()
        if not a_status:
            status = "AA"
        elif a_status in ["aw", "cw", "vw"]:
            status = a_status.upper()
        elif a_status == "audit":
            status = "SA"
        else:
            assert False, "unknown classlist student status indicator: " + repr(rec)
    elif "REGISTRATION_STATUS" in rec:
        # source == 'report'
        if rec["REGISTRATION_STATUS"] in ["RW", "RE"]:  # Registered Web/???
            status = "AA"
        elif rec["REGISTRATION_STATUS"] == "DW":  # Drop Web
            status = "VW"
        else:
            assert False, "unknown report student status indicator: " + repr(rec)
    else:
        raise RuntimeError("Unknown student record source")
    return status


################################################################


def _dict_queryset_delta(old_qs, new_dict, key_field):
    """
    Given an existing queryset and a dictionary of new items,
    (and the name of the field used as the key)
    partition the information into
    ``create_dict`` - a subset of ``new_dict`` that requires creation
    ``exists_qs`` - a subset of ``old_qs`` which *may* need updating
    ``expire_qs`` - a subset of ``old_qs`` which **is not** in ``new_dict``.
    """
    key_list = new_dict.keys()
    exists_qs = old_qs.filter(**{"{0}__in".format(key_field): key_list})
    exists_pks = exists_qs.values_list("pk", flat=True)
    expire_qs = old_qs.exclude(pk__in=exists_pks)
    new_keys = set(key_list).difference(set(exists_pks))
    create_dict = {key: new_dict[key] for key in new_keys}
    return create_dict, exists_qs, expire_qs


################################################################


def update_registrations(
    fileobj,
    section=None,
    return_invalid_logins=False,
    require_valid_login=False,
    ignore_unknown_sections=False,
    valid_status=None,
    commit=True,
    source=None,
    request_user=None,
):
    """
    Update Registrations based on the Aurora CSV file given.
    ``valid_status``, if given, must be a list of valid "Reg Status" values;
    use an empty list for any status.

    ``source = "classlist"`` is equivalent to ``source = None``
    ``source = "report"`` is also valid.
    """
    # Cross check to see if parameters make sense with configuration.
    #   - if we cannot have usernames, do the right thing.
    if conf.get("aurora:student_username") is None:
        return_invalid_logins = False
        require_value_login = False

    if valid_status is None:
        valid_status = ["startswith:registered"]

    if source is None:
        source = "classlist"
    if source == "report":
        valid_status = None  # not applicable in this case.

    if source not in ["classlist", "report"]:
        raise RuntimeError("Not a valid source")

    if source == "classlist":
        aurora_section_qs, a_students = read_classlist(fileobj)
    else:
        aurora_section_qs, a_students = read_report(fileobj)

    def _s_cmp(s, v):
        s = s.lower()
        v = v.lower()
        if ":" in v:
            op, v = v.split(":", 1)
        else:
            op = "exact"
        if op == "exact":
            return s == v
        if op == "startswith":
            return s.startswith(v)
        raise RuntimeError("unimplmented comparison operator {!r}".format(op))

    if valid_status:
        status_cmp = [lambda s: _s_cmp(s, v) for v in valid_status]
        a_students = [
            st for st in a_students if any([c(st["Reg Status"]) for c in status_cmp])
        ]

    if source == "classlist":
        if section is None:
            if aurora_section_qs.count() == 1:
                section = aurora_section_qs.get()
        else:
            if section.pk not in aurora_section_qs.values_list("id", flat=True):
                raise WrongSection("Sections do not match")

        if section is None:
            raise WrongSection("Could not determine section")

    # This might be short circuiting a bit early...
    section_cache = {}  # only used when ``source == 'report'``
    if not commit:
        if source == "report":
            # need to see if there are invalid sections...
            for rec in a_students:
                section = _get_report_section(rec, aurora_section_qs, section_cache)
                if section is None and not ignore_unknown_sections:
                    raise InvalidSection("There is an unknown section in this report")
        return {}

    if return_invalid_logins:
        invalid_logins = []

    valid_student_numbers = []
    # sections agree, proceed

    id_list = [rec["ID"] for rec in a_students]
    email_list = [rec["Email"] for rec in a_students]
    username_list = [_get_username(e) for e in email_list]
    name_list = [rec["Student Name"] for rec in a_students]
    status_list = [_get_status(rec) for rec in a_students]

    # strategy:
    # - get current registrations
    # - delta on a_students: create regs, update regs, deactive regs
    # - process corresponding people,  and delta on them.

    ignore_student_count = 0
    saved_student_count = 0
    total_student_count = 0
    for rec in a_students:
        total_student_count += 1
        if source == "report":
            section = _get_report_section(rec, aurora_section_qs, section_cache)
            if section is None:
                if ignore_unknown_sections:
                    ignore_student_count += 1
                    continue
                else:
                    raise InvalidSection("There is an unknown section in this report")
        #         pprint(rec)
        try:
            student = get_or_create_student(
                rec, section, require_valid_login, request_user
            )
        except InvalidUsername as invalid:
            if return_invalid_logins:
                invalid_logins.append(str(invalid))
            continue

        if return_invalid_logins and (
            student.person.username is None or student.person.username[0] == "!"
        ):
            invalid_logins.append(
                "%s [%d] does not have a valid username"
                % ("{}".format(student), student.student_number)
            )
        status = _get_status(rec)
        reg = update_or_create_registration(
            section, student, status, require_valid_login, request_user
        )
        valid_student_numbers.append(reg.student.student_number)
        saved_student_count += 1

    # de-register non-verifications
    dereg_list = Student_Registration.objects.filter(
        active=True, section__in=aurora_section_qs
    ).exclude(student__student_number__in=valid_student_numbers)
    dereg_list = dereg_list.exclude(status="N")
    for reg in dereg_list:
        reg.student.History_Update(
            "aurora2.aurora_filter",
            "de-registered student: not (valid) on Aurora class list for {} ({})".format(
                reg.section, reg.section.term
            ),
            subobj=reg,
            user=request_user,
        )
        reg.status = "N"
        reg.save()
    # Using update does not fire a gradebook signal.
    # dereg_list.update(status='N')

    return_vals = {}
    if return_invalid_logins:
        return_vals["invalid_logins"] = invalid_logins

    if section is None and source == "classlist":
        return_vals["section"] = section

    return_vals["total_student_count"] = total_student_count
    return_vals["section_ignore_student_count"] = ignore_student_count
    return_vals["saved_student_count"] = saved_student_count

    return return_vals


################################################################

#
