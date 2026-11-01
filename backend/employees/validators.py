import re

from django.core.exceptions import ValidationError

NATIONAL_ID_RE = re.compile(r"^\d{13}$")
MOBILE_RE = re.compile(r"^03\d{9}$")


def normalise_national_id(value: str) -> str:
    """Strip dashes and spaces: '42101-1234567-1' -> '4210112345671'."""
    return re.sub(r"[\s-]", "", value or "")


def validate_national_id(value: str):
    if value and not NATIONAL_ID_RE.match(value):
        raise ValidationError("National ID must be exactly 13 digits with no dashes.")


def validate_mobile(value: str):
    if value and not MOBILE_RE.match(value):
        raise ValidationError("Mobile number must be 11 digits starting with 03.")
