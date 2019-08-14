"""
The DEFAULT configuration is loaded when the named _CONFIG dictionary
is not present in your settings.
"""

CONFIG_NAME = "STUDENTS_CONFIG"  # must be uppercase!


def aurora_student_username(email):
    """
    Default callable to mogrify an email address to a username.
    Should return ``None`` when a username cannot be determined.
    (Note this this callable returning ``None`` is **not** the same
     as setting the CONFIG value ``aurora:student_username`` to ``None``.)
    """
    if email.lower().endswith("@cc.umanitoba.ca"):
        return email.split("@")[0].lower()  # real umnetid
    if email.lower().endswith("@myumanitoba.ca"):
        return email.split("@")[0].lower()  # real umnetid
    return None


def aurora_email_type_slug(email):
    """
    This callable must always return a valid email type slug.
    """
    if email.lower().endswith("@cc.umanitoba.ca"):
        return "work"
    if email.lower().endswith("@myumanitoba.ca"):
        return "work"
    return "home"


DEFAULT = {
    # A callable that mogrifies an email address to a username.
    #   This can be 'None', in which case student usernames are never set.
    "aurora:student_username": aurora_student_username,
    # A callable that determines the type of email address.
    #   Use ``lambda e: 'work'`` for a static value.
    "aurora:email_type_slug": aurora_email_type_slug,
    # Whether or not to use django admin history as well
    #   as student history
    "history:django_admin": True,
}

#########################################################################

from django.conf import settings


def get(setting):
    """
    get(setting) -> value

    setting should be a string representing the application settings to
    retrieve.
    """
    assert setting in DEFAULT, "the setting %r has no default value" % setting
    app_settings = getattr(settings, CONFIG_NAME, DEFAULT)
    return app_settings.get(setting, DEFAULT[setting])


def get_all():
    """
    Return all current settings as a dictionary.
    """
    app_settings = getattr(settings, CONFIG_NAME, DEFAULT)
    return dict(
        [(setting, app_settings.get(setting, DEFAULT[setting])) for setting in DEFAULT]
    )


#########################################################################
