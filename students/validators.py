import os

from django.core.exceptions import ValidationError


def _validate_file_extension(value, *valid_extensions):
    ext = os.path.splitext(value.name)[1]
    if not ext.lower() in valid_extensions:
        raise ValidationError("Unsupported file type.")


def validate_csv_file_extension(value):
    return _validate_file_extension(value, ".csv")
