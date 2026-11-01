from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from accounts.permissions import ROLE_ADMIN, ROLE_OFFICER, ROLE_VIEWER
from employees.models import Employee
from masters.models import Department, Designation, EmploymentType, Location


@pytest.fixture
def masters(db):
    return {
        "hr": Department.objects.create(code="HR", name="Human Resources"),
        "fin": Department.objects.create(code="FIN", name="Finance"),
        "officer": Designation.objects.create(title="Officer", grade=11, category="Officer"),
        "manager": Designation.objects.create(title="Manager", grade=15, category="Manager"),
        "assistant": Designation.objects.create(title="Assistant", grade=8, category="Staff"),
        "permanent": EmploymentType.objects.create(name="Permanent", is_contractual=False),
        "contract": EmploymentType.objects.create(name="Contract", is_contractual=True),
        "loc": Location.objects.create(name="Head Office", city="Karachi"),
    }


@pytest.fixture
def make_employee(masters):
    counter = {"n": 0}

    def _make(**kw):
        counter["n"] += 1
        data = dict(
            employee_no=f"T-{counter['n']:03d}", full_name=f"Test Person {counter['n']}",
            department=masters["hr"], designation=masters["officer"], employment_type=masters["permanent"],
            location=masters["loc"], join_date=date(2020, 1, 1), dob=date(1990, 5, 5),
            basic_pay=Decimal("100000"), allowances=Decimal("30000"),
        )
        data.update(kw)
        return Employee.objects.create(**data)
    return _make


def _user(username, role):
    u = User.objects.create_user(username, password="pw-123456")
    u.groups.add(Group.objects.get_or_create(name=role)[0])
    return u


@pytest.fixture
def admin_client(db):
    c = APIClient()
    c.force_authenticate(_user("adm", ROLE_ADMIN))
    return c


@pytest.fixture
def officer_client(db):
    c = APIClient()
    c.force_authenticate(_user("off", ROLE_OFFICER))
    return c


@pytest.fixture
def viewer_client(db):
    c = APIClient()
    c.force_authenticate(_user("view", ROLE_VIEWER))
    return c


@pytest.fixture
def today():
    return date.today()


@pytest.fixture
def soon(today):
    return today + timedelta(days=30)
