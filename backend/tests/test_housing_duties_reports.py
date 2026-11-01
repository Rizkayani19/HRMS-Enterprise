import calendar
from datetime import date, timedelta

import pytest
from rest_framework.exceptions import ValidationError

from duties.models import DutyAssignment, DutyType
from duties.services import generate_roster
from employees.models import Employee
from housing import services as housing
from housing.models import HousingUnit, WaitingListEntry
from reports.registry import REPORTS


@pytest.fixture
def unit(db):
    return HousingUnit.objects.create(code="A-01", block="Block A", category="Family Flat", min_grade=11)


def test_allot_and_vacate(make_employee, unit, today):
    e = make_employee()
    WaitingListEntry.objects.create(employee=e, category="Family Flat", registered_on=today)
    housing.allot(unit, e, today)
    assert unit.current_allotment.employee == e
    assert not WaitingListEntry.objects.exists()
    housing.vacate(unit, today)
    assert unit.current_allotment is None


def test_cannot_double_allot(make_employee, unit, today):
    housing.allot(unit, make_employee(), today)
    with pytest.raises(ValidationError):
        housing.allot(unit, make_employee(), today)


def test_one_unit_per_employee(make_employee, unit, today):
    e = make_employee()
    other = HousingUnit.objects.create(code="A-02", block="Block A", category="Family Flat", min_grade=11)
    housing.allot(unit, e, today)
    with pytest.raises(ValidationError):
        housing.allot(other, e, today)


def test_grade_entitlement_enforced(make_employee, masters, unit, today):
    with pytest.raises(ValidationError):
        housing.allot(unit, make_employee(designation=masters["assistant"]), today)


def test_unserviceable_unit_rejected(make_employee, unit, today):
    unit.is_serviceable = False
    unit.save()
    with pytest.raises(ValidationError):
        housing.allot(unit, make_employee(), today)


def test_waiting_list_seniority_order(make_employee, today):
    late, early = make_employee(), make_employee()
    WaitingListEntry.objects.create(employee=late, category="Family Flat", registered_on=today)
    WaitingListEntry.objects.create(employee=early, category="Family Flat", registered_on=today - timedelta(days=90))
    assert [w.employee for w in housing.waiting_list()] == [early, late]


def test_roster_is_fair_and_has_no_clashes(make_employee, today):
    staff = [make_employee() for _ in range(5)]
    make_employee(status=Employee.STATUS_ON_LEAVE)
    DutyType.objects.create(name="Night Duty", min_grade=1, max_grade=20)
    DutyType.objects.create(name="Gate Duty", min_grade=1, max_grade=20)
    n = generate_roster(today.year, today.month)
    days = calendar.monthrange(today.year, today.month)[1]
    assert n == days * 2
    counts = [DutyAssignment.objects.filter(employee=e).count() for e in staff]
    assert max(counts) - min(counts) <= 1
    for d in range(1, days + 1):
        people = DutyAssignment.objects.filter(date=date(today.year, today.month, d)).values_list("employee", flat=True)
        assert len(people) == len(set(people))
    assert not DutyAssignment.objects.filter(employee__status=Employee.STATUS_ON_LEAVE).exists()


def test_weekend_only_duty(make_employee, today):
    make_employee()
    DutyType.objects.create(name="Weekend", min_grade=1, max_grade=20, weekends_only=True)
    generate_roster(today.year, today.month)
    assert all(a.date.weekday() >= 5 for a in DutyAssignment.objects.all())


def test_roster_respects_grade_band(make_employee, masters, today):
    make_employee(designation=masters["assistant"])
    DutyType.objects.create(name="Managers only", min_grade=15, max_grade=20)
    assert generate_roster(today.year, today.month) == 0


@pytest.mark.parametrize("report", REPORTS, ids=lambda r: r.key)
@pytest.mark.parametrize("fmt", ["", "pdf/", "xlsx/", "csv/"])
def test_every_report_renders(admin_client, make_employee, report, fmt):
    make_employee()
    r = admin_client.get(f"/api/reports/{report.key}/{fmt}")
    assert r.status_code == 200
    if fmt == "pdf/":
        assert r.content.startswith(b"%PDF")


def test_unknown_report_404(admin_client):
    assert admin_client.get("/api/reports/nope/").status_code == 404
