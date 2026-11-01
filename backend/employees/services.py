"""Lifecycle business rules. Each function runs in a transaction and writes an audit entry."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import AuditLog

from .models import (
    ContractExtension, DepartmentTransfer, Employee, EmploymentTypeChange, ExitRecord, Promotion,
)


def _ensure_not_exited(emp):
    if emp.status == Employee.STATUS_EXITED:
        raise ValidationError(f"{emp.employee_no} has already exited.")


@transaction.atomic
def transfer(emp, to_department, effective_date, user=None, order_ref="", reason=""):
    _ensure_not_exited(emp)
    if emp.department_id == to_department.id:
        raise ValidationError("Employee is already in that department.")
    rec = DepartmentTransfer.objects.create(
        employee=emp, from_department=emp.department, to_department=to_department,
        effective_date=effective_date, order_ref=order_ref, reason=reason,
    )
    emp.department = to_department
    emp.save(update_fields=["department", "updated_at"])
    AuditLog.record(user, "transfer", f"{emp.employee_no}: {rec.from_department.code} -> {to_department.code}")
    return rec


@transaction.atomic
def promote(emp, to_designation, effective_date, user=None, order_ref="", new_basic_pay=None):
    _ensure_not_exited(emp)
    if to_designation.grade <= emp.designation.grade:
        raise ValidationError("A promotion must be to a higher grade.")
    rec = Promotion.objects.create(
        employee=emp, from_designation=emp.designation, to_designation=to_designation,
        effective_date=effective_date, order_ref=order_ref,
    )
    emp.designation = to_designation
    emp.grade_seniority_date = effective_date
    fields = ["designation", "grade_seniority_date", "updated_at"]
    if new_basic_pay is not None:
        emp.basic_pay = new_basic_pay
        fields.append("basic_pay")
    emp.save(update_fields=fields)
    AuditLog.record(user, "promotion", f"{emp.employee_no}: {rec.from_designation.title} -> {to_designation.title}")
    return rec


@transaction.atomic
def extend_contract(emp, new_end, user=None, new_start=None, new_basic_pay=None, order_ref=""):
    _ensure_not_exited(emp)
    if not emp.employment_type.is_contractual:
        raise ValidationError("Only contractual employees can have their contract extended.")
    start = new_start or (emp.contract_end + timezone.timedelta(days=1) if emp.contract_end else timezone.localdate())
    if new_end <= start:
        raise ValidationError("New contract end must be after its start.")
    pay_revised = new_basic_pay is not None and new_basic_pay != emp.basic_pay
    rec = ContractExtension.objects.create(
        employee=emp, previous_end=emp.contract_end, new_start=start, new_end=new_end,
        pay_revised=pay_revised, old_basic_pay=emp.basic_pay if pay_revised else None,
        new_basic_pay=new_basic_pay if pay_revised else None, order_ref=order_ref,
    )
    emp.contract_start, emp.contract_end = start, new_end
    if pay_revised:
        emp.basic_pay = new_basic_pay
    emp.save()
    AuditLog.record(user, "contract_extension", f"{emp.employee_no}: until {new_end}" + (" with pay revision" if pay_revised else ""))
    return rec


@transaction.atomic
def change_employment_type(emp, to_type, effective_date, user=None, order_ref="", contract_end=None):
    _ensure_not_exited(emp)
    if emp.employment_type_id == to_type.id:
        raise ValidationError("Employee already has that employment type.")
    if to_type.is_contractual and not contract_end:
        raise ValidationError("A contract end date is required when converting to a contractual type.")
    rec = EmploymentTypeChange.objects.create(
        employee=emp, from_type=emp.employment_type, to_type=to_type,
        effective_date=effective_date, order_ref=order_ref,
    )
    emp.employment_type = to_type
    if to_type.is_contractual:
        emp.contract_start, emp.contract_end = effective_date, contract_end
    else:
        emp.contract_start = emp.contract_end = None
    emp.save()
    AuditLog.record(user, "type_change", f"{emp.employee_no}: {rec.from_type.name} -> {to_type.name}")
    return rec


@transaction.atomic
def exit_employee(emp, exit_date, category, user=None, destination="", reliever="", handover_notes=""):
    """Archive an employee: closes housing and waiting-list entries and flags housing vacation."""
    from housing.models import Allotment, WaitingListEntry

    _ensure_not_exited(emp)
    allotment = Allotment.objects.filter(employee=emp, vacated_on__isnull=True).first()
    rec = ExitRecord.objects.create(
        employee=emp, exit_date=exit_date, category=category, destination=destination,
        reliever=reliever, handover_notes=handover_notes, housing_vacation_due=bool(allotment),
    )
    if allotment:
        allotment.vacated_on = exit_date
        allotment.save(update_fields=["vacated_on"])
    WaitingListEntry.objects.filter(employee=emp).delete()
    emp.status = Employee.STATUS_EXITED
    emp.save(update_fields=["status", "updated_at"])
    AuditLog.record(user, "exit", f"{emp.employee_no}: {category} on {exit_date}")
    return rec


@transaction.atomic
def bulk_update_status(employees, status, user=None):
    if status == Employee.STATUS_EXITED:
        raise ValidationError("Use the exit action to archive employees.")
    count = 0
    for emp in employees:
        if emp.status != Employee.STATUS_EXITED:
            emp.status = status
            emp.save(update_fields=["status", "updated_at"])
            count += 1
    AuditLog.record(user, "bulk_status", f"{count} employees -> {status}")
    return count


@transaction.atomic
def bulk_transfer(employees, to_department, effective_date, user=None, order_ref=""):
    done = 0
    for emp in employees:
        if emp.status != Employee.STATUS_EXITED and emp.department_id != to_department.id:
            transfer(emp, to_department, effective_date, user=user, order_ref=order_ref, reason="Bulk transfer")
            done += 1
    return done
