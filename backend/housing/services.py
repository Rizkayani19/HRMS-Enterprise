from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import AuditLog
from employees.models import Employee

from .models import Allotment, HousingUnit, WaitingListEntry


def waiting_list(category=None):
    """Waiting list in seniority order (earliest registration first)."""
    qs = WaitingListEntry.objects.select_related("employee__designation", "employee__department").filter(
        employee__status__in=[Employee.STATUS_ACTIVE, Employee.STATUS_ON_LEAVE]
    )
    if category:
        qs = qs.filter(category=category)
    return list(qs.order_by("registered_on", "employee__employee_no"))


@transaction.atomic
def allot(unit: HousingUnit, employee: Employee, occupied_from, user=None):
    if not unit.is_serviceable:
        raise ValidationError("This unit is marked unserviceable.")
    if unit.current_allotment:
        raise ValidationError(f"{unit.code} is already occupied.")
    if employee.status == Employee.STATUS_EXITED:
        raise ValidationError("Cannot allot housing to an exited employee.")
    if Allotment.objects.filter(employee=employee, vacated_on__isnull=True).exists():
        raise ValidationError(f"{employee.employee_no} already holds a housing unit.")
    if employee.designation.grade < unit.min_grade:
        raise ValidationError(f"{unit.code} requires grade {unit.min_grade} or above.")
    a = Allotment.objects.create(unit=unit, employee=employee, occupied_from=occupied_from)
    WaitingListEntry.objects.filter(employee=employee).delete()
    AuditLog.record(user, "housing_allot", f"{unit.code} -> {employee.employee_no}")
    return a


@transaction.atomic
def vacate(unit: HousingUnit, vacated_on, user=None):
    a = unit.current_allotment
    if not a:
        raise ValidationError(f"{unit.code} is already vacant.")
    a.vacated_on = vacated_on
    a.save(update_fields=["vacated_on"])
    AuditLog.record(user, "housing_vacate", f"{unit.code} vacated by {a.employee.employee_no}")
    return a
