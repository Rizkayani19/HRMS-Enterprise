from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from employees import services
from employees.models import Employee
from housing.models import Allotment, HousingUnit, WaitingListEntry


def test_transfer_records_history(make_employee, masters, today):
    e = make_employee()
    services.transfer(e, masters["fin"], today, order_ref="T/1")
    e.refresh_from_db()
    assert e.department == masters["fin"]
    t = e.transfers.get()
    assert t.from_department == masters["hr"] and t.to_department == masters["fin"]


def test_transfer_to_same_department_rejected(make_employee, masters, today):
    with pytest.raises(ValidationError):
        services.transfer(make_employee(), masters["hr"], today)


def test_promotion_must_raise_grade(make_employee, masters, today):
    e = make_employee(designation=masters["officer"])
    with pytest.raises(ValidationError):
        services.promote(e, masters["assistant"], today)
    services.promote(e, masters["manager"], today, new_basic_pay=Decimal("200000"))
    e.refresh_from_db()
    assert e.designation == masters["manager"] and e.grade_seniority_date == today
    assert e.basic_pay == Decimal("200000")


def test_contract_extension_with_pay_revision(make_employee, masters, today):
    e = make_employee(employment_type=masters["contract"], contract_start=today - timedelta(days=300),
                      contract_end=today + timedelta(days=65))
    rec = services.extend_contract(e, today + timedelta(days=430), new_basic_pay=Decimal("110000"))
    e.refresh_from_db()
    assert rec.pay_revised and rec.old_basic_pay == Decimal("100000")
    assert e.basic_pay == Decimal("110000") and e.contract_end == today + timedelta(days=430)
    assert rec.new_start == today + timedelta(days=66)


def test_extension_without_pay_change(make_employee, masters, today):
    e = make_employee(employment_type=masters["contract"], contract_end=today + timedelta(days=10))
    rec = services.extend_contract(e, today + timedelta(days=400))
    assert rec.pay_revised is False and rec.old_basic_pay is None


def test_permanent_staff_cannot_be_extended(make_employee, today):
    with pytest.raises(ValidationError):
        services.extend_contract(make_employee(), today + timedelta(days=365))


def test_type_conversion_keeps_single_profile(make_employee, masters, today):
    e = make_employee(employment_type=masters["contract"], contract_start=today, contract_end=today + timedelta(days=300))
    services.change_employment_type(e, masters["permanent"], today)
    e.refresh_from_db()
    assert e.employment_type == masters["permanent"] and e.contract_end is None
    assert Employee.objects.count() == 1 and e.type_changes.count() == 1


def test_conversion_to_contract_needs_end_date(make_employee, masters, today):
    with pytest.raises(ValidationError):
        services.change_employment_type(make_employee(), masters["contract"], today)


def test_exit_vacates_housing_and_flags_it(make_employee, today):
    e = make_employee()
    unit = HousingUnit.objects.create(code="A-1", block="A", category="Family Flat", min_grade=1)
    Allotment.objects.create(unit=unit, employee=e, occupied_from=date(2022, 1, 1))
    rec = services.exit_employee(e, today, "Resignation")
    e.refresh_from_db()
    assert e.status == Employee.STATUS_EXITED and rec.housing_vacation_due
    assert unit.current_allotment is None


def test_exit_removes_waiting_list_entry(make_employee, today):
    e = make_employee()
    WaitingListEntry.objects.create(employee=e, category="Family Flat", registered_on=today)
    services.exit_employee(e, today, "Retirement")
    assert not WaitingListEntry.objects.exists()


def test_actions_on_exited_employee_rejected(make_employee, masters, today):
    e = make_employee(status=Employee.STATUS_EXITED)
    with pytest.raises(ValidationError):
        services.transfer(e, masters["fin"], today)


def test_bulk_status_skips_exited_and_refuses_exit(make_employee):
    a, b = make_employee(), make_employee(status=Employee.STATUS_EXITED)
    assert services.bulk_update_status([a, b], Employee.STATUS_ON_LEAVE) == 1
    with pytest.raises(ValidationError):
        services.bulk_update_status([a], Employee.STATUS_EXITED)


def test_bulk_transfer_api(officer_client, make_employee, masters, today):
    ids = [make_employee().id for _ in range(3)]
    r = officer_client.post("/api/employees/bulk/", {"ids": ids, "action": "transfer",
                                                     "to_department": masters["fin"].id,
                                                     "effective_date": str(today)}, format="json")
    assert r.data["updated"] == 3
    assert Employee.objects.filter(department=masters["fin"]).count() == 3


def test_lifecycle_endpoints(officer_client, make_employee, masters, today):
    e = make_employee()
    r = officer_client.post(f"/api/employees/{e.id}/transfer/", {"to_department": masters["fin"].id,
                                                                 "effective_date": str(today)}, format="json")
    assert r.status_code == 200 and r.data["department_name"] == "Finance"
    r = officer_client.post(f"/api/employees/{e.id}/exit/", {"exit_date": str(today), "category": "Resignation"},
                            format="json")
    assert r.status_code == 200 and r.data["status"] == "Exited"
