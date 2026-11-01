from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from accounts.models import AuditLog
from employees.models import Employee
from employees.validators import validate_mobile, validate_national_id


def test_national_id_dashes_are_stripped(make_employee):
    e = make_employee(national_id="42101-1234567-1")
    assert e.national_id == "4210112345671"


@pytest.mark.parametrize("value", ["123", "12345678901234", "42101A2345671"])
def test_national_id_must_be_13_digits(value):
    with pytest.raises(ValidationError):
        validate_national_id(value)


def test_mobile_validation():
    validate_mobile("03001234567")
    with pytest.raises(ValidationError):
        validate_mobile("3001234567")


def test_retirement_date_is_age_60(make_employee):
    e = make_employee(dob=date(1970, 3, 15))
    assert e.retirement_date == date(2030, 3, 15)


def test_retirement_date_leap_day(make_employee):
    e = make_employee(dob=date(1972, 2, 29))
    assert e.retirement_date == date(2032, 2, 28) or e.retirement_date == date(2032, 2, 29)


def test_gross_pay(make_employee):
    assert make_employee().gross_pay == Decimal("130000")


def test_create_via_api_with_children(officer_client, masters):
    payload = {
        "employee_no": "NEW-1", "full_name": "Sara Example", "department": masters["hr"].id,
        "designation": masters["officer"].id, "employment_type": masters["permanent"].id,
        "join_date": "2024-01-01", "national_id": "42101-0000000-1", "mobile": "03001112223",
        "family": [{"relationship": "Spouse", "name": "Ali Example"}],
        "previous_appointments": [{"organisation": "Acme", "title": "Officer"}],
    }
    r = officer_client.post("/api/employees/", payload, format="json")
    assert r.status_code == 201, r.data
    assert r.data["national_id"] == "4210100000001"
    assert len(r.data["family"]) == 1 and len(r.data["previous_appointments"]) == 1
    assert AuditLog.objects.filter(action="create").exists()


def test_update_replaces_previous_appointments(officer_client, make_employee):
    e = make_employee()
    url = f"/api/employees/{e.id}/"
    officer_client.patch(url, {"previous_appointments": [{"organisation": "A", "title": "X"},
                                                         {"organisation": "B", "title": "Y"}]}, format="json")
    r = officer_client.patch(url, {"previous_appointments": [{"organisation": "C", "title": "Z"}]}, format="json")
    assert [a["organisation"] for a in r.data["previous_appointments"]] == ["C"]


def test_contractual_requires_contract_end(officer_client, masters):
    r = officer_client.post("/api/employees/", {
        "employee_no": "C-1", "full_name": "C", "department": masters["hr"].id,
        "designation": masters["officer"].id, "employment_type": masters["contract"].id, "join_date": "2024-01-01",
    }, format="json")
    assert r.status_code == 400 and "contract_end" in r.data


def test_employees_cannot_be_deleted(admin_client, make_employee):
    e = make_employee()
    assert admin_client.delete(f"/api/employees/{e.id}/").status_code == 405
    assert Employee.objects.filter(id=e.id).exists()


def test_list_filters_and_search(admin_client, make_employee, masters):
    make_employee(full_name="Zubair Finance", department=masters["fin"])
    make_employee(full_name="Hina HR")
    assert len(admin_client.get(f"/api/employees/?department={masters['fin'].id}").data) == 1
    assert len(admin_client.get("/api/employees/?q=hina").data) == 1


def test_list_hides_exited_unless_archived(admin_client, make_employee):
    make_employee()
    make_employee(status=Employee.STATUS_EXITED)
    assert len(admin_client.get("/api/employees/").data) == 1
    assert len(admin_client.get("/api/employees/?archived=1").data) == 1


def test_csv_export(admin_client, make_employee):
    make_employee(full_name="Export Me")
    r = admin_client.get("/api/employees/export-csv/")
    assert r.status_code == 200 and b"Export Me" in r.content


def test_dashboard(admin_client, make_employee, today):
    make_employee(dob=today.replace(year=today.year - 60) + timedelta(days=30))
    r = admin_client.get("/api/dashboard/")
    assert r.data["headcount"] == 1 and len(r.data["retiring"]) == 1
