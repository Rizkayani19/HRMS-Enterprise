"""Report definitions. Each report returns a title, column headings and rows."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from django.db.models import Count

from duties.models import DutyAssignment
from employees.models import DepartmentTransfer, Employee, ExitRecord
from housing.models import Allotment, HousingUnit
from housing.services import waiting_list
from masters.models import Department, Designation


@dataclass
class ReportResult:
    title: str
    columns: list
    rows: list
    subtitle: str = ""
    landscape: bool = True


@dataclass
class Report:
    key: str
    title: str
    description: str
    build: Callable
    params: list = field(default_factory=list)


def _active():
    return (Employee.objects.exclude(status=Employee.STATUS_EXITED)
            .select_related("department", "designation", "employment_type", "location"))


def _d(v):
    return v.strftime("%d %b %Y") if v else ""


def nominal_roll(p):
    rows = []
    for dept in Department.objects.all():
        staff = _active().filter(department=dept)
        for i, e in enumerate(staff, 1):
            rows.append([dept.name, i, e.employee_no, e.full_name, e.designation.title, e.designation.grade,
                         e.employment_type.name, _d(e.join_date), e.status])
    return ReportResult("Nominal Roll", ["Department", "S/No", "Emp No", "Name", "Designation", "Grade",
                                         "Type", "Joined", "Status"], rows,
                        f"Active strength by department, in order of seniority - {len(rows)} employees")


def staff_directory(p):
    rows = [[e.full_name, e.designation.title, e.department.name, e.office_ext, e.mobile, e.email]
            for e in _active().order_by("department__name", "-designation__grade", "full_name")]
    return ReportResult("Staff Telephone Directory", ["Name", "Designation", "Department", "Ext", "Mobile", "Email"], rows)


def contract_expiry(p):
    days = int(p.get("days") or 90)
    today = date.today()
    qs = _active().filter(contract_end__isnull=False, contract_end__lte=today + timedelta(days=days)).order_by("contract_end")
    rows = [[e.employee_no, e.full_name, e.designation.title, e.department.name, _d(e.contract_start),
             _d(e.contract_end), (e.contract_end - today).days] for e in qs]
    return ReportResult("Contract Expiry Schedule", ["Emp No", "Name", "Designation", "Department", "Contract Start",
                                                     "Contract End", "Days Left"], rows,
                        f"Contracts ending within {days} days (negative = already expired)")


def retirements(p):
    months = int(p.get("months") or 24)
    today = date.today()
    limit = today + timedelta(days=int(months * 30.44))
    emps = [e for e in _active().exclude(dob=None) if e.retirement_date and e.retirement_date <= limit]
    emps.sort(key=lambda e: e.retirement_date)
    rows = [[e.employee_no, e.full_name, e.designation.title, e.department.name, _d(e.dob), _d(e.retirement_date),
             e.years_of_service] for e in emps]
    return ReportResult("Retirements Due", ["Emp No", "Name", "Designation", "Department", "Date of Birth",
                                            "Retirement Date", "Years of Service"], rows,
                        f"Staff reaching retirement age within {months} months")


def headcount(p):
    qs = _active().values("department__name", "employment_type__name").annotate(n=Count("id"))
    types = sorted({r["employment_type__name"] for r in qs})
    grid = defaultdict(Counter)
    for r in qs:
        grid[r["department__name"]][r["employment_type__name"]] = r["n"]
    rows = [[d] + [grid[d][t] for t in types] + [sum(grid[d].values())] for d in sorted(grid)]
    rows.append(["TOTAL"] + [sum(grid[d][t] for d in grid) for t in types] + [sum(sum(c.values()) for c in grid.values())])
    return ReportResult("Headcount by Department", ["Department"] + types + ["Total"], rows, landscape=False)


def grade_strength(p):
    qs = _active().values("designation__grade", "designation__category").annotate(n=Count("id")).order_by("-designation__grade")
    rows = [[f"G-{r['designation__grade']}", r["designation__category"], r["n"]] for r in qs]
    return ReportResult("Grade-wise Strength", ["Grade", "Category", "Employees"], rows, landscape=False)


def housing_allotments(p):
    rows = []
    for u in HousingUnit.objects.all():
        a = u.current_allotment
        rows.append([u.code, u.block, u.category, f"G-{u.min_grade}+",
                     a.employee.full_name if a else ("Unserviceable" if not u.is_serviceable else "VACANT"),
                     a.employee.employee_no if a else "", _d(a.occupied_from) if a else ""])
    return ReportResult("Housing Allotment Register", ["Unit", "Block", "Category", "Entitlement", "Occupant",
                                                       "Emp No", "Occupied From"], rows)


def housing_waiting(p):
    rows = [[i, w.employee.employee_no, w.employee.full_name, w.employee.designation.title,
             w.employee.designation.grade, w.category, _d(w.registered_on)]
            for i, w in enumerate(waiting_list(p.get("category")), 1)]
    return ReportResult("Housing Waiting List", ["Seniority", "Emp No", "Name", "Designation", "Grade",
                                                 "Category", "Registered On"], rows, "In order of registration date")


def duty_roster(p):
    today = date.today()
    year, month = int(p.get("year") or today.year), int(p.get("month") or today.month)
    qs = DutyAssignment.objects.filter(date__year=year, date__month=month).select_related("duty_type", "employee__designation")
    rows = [[_d(a.date), a.date.strftime("%a"), a.duty_type.name, a.employee.full_name, a.employee.designation.title,
             a.employee.office_ext] for a in qs]
    return ReportResult("Duty Roster", ["Date", "Day", "Duty", "Name", "Designation", "Ext"], rows,
                        date(year, month, 1).strftime("%B %Y"))


def transfers_log(p):
    qs = DepartmentTransfer.objects.select_related("employee", "from_department", "to_department")[:500]
    rows = [[_d(t.effective_date), t.employee.employee_no, t.employee.full_name, t.from_department.name,
             t.to_department.name, t.order_ref, t.reason] for t in qs]
    return ReportResult("Inter-Department Transfer Log", ["Effective", "Emp No", "Name", "From", "To", "Order Ref",
                                                          "Reason"], rows)


def exits_register(p):
    qs = ExitRecord.objects.select_related("employee__designation").order_by("-exit_date")
    rows = [[_d(x.exit_date), x.employee.employee_no, x.employee.full_name, x.employee.designation.title, x.category,
             x.destination, "Yes" if x.housing_vacation_due else ""] for x in qs]
    return ReportResult("Exit & Archive Register", ["Exit Date", "Emp No", "Name", "Designation", "Category",
                                                    "Destination", "Housing to Vacate"], rows)


def pay_summary(p):
    rows, total = [], 0
    for dept in Department.objects.all():
        staff = _active().filter(department=dept)
        gross = sum(e.gross_pay for e in staff)
        total += gross
        rows.append([dept.name, staff.count(), f"{gross:,.0f}"])
    rows.append(["TOTAL", _active().count(), f"{total:,.0f}"])
    return ReportResult("Monthly Pay Bill by Department", ["Department", "Employees", "Gross Pay (Rs)"], rows,
                        landscape=False)


REPORTS = [
    Report("nominal-roll", "Nominal Roll", "Department-wise strength in seniority order.", nominal_roll),
    Report("staff-directory", "Staff Telephone Directory", "Extensions, mobiles and emails.", staff_directory),
    Report("contract-expiry", "Contract Expiry Schedule", "Contracts ending soon.", contract_expiry, ["days"]),
    Report("retirements", "Retirements Due", "Staff reaching retirement age.", retirements, ["months"]),
    Report("headcount", "Headcount by Department", "Strength by department and employment type.", headcount),
    Report("grade-strength", "Grade-wise Strength", "Strength by pay grade.", grade_strength),
    Report("pay-summary", "Monthly Pay Bill", "Gross pay by department.", pay_summary),
    Report("housing-allotments", "Housing Allotment Register", "Every unit and its occupant.", housing_allotments),
    Report("housing-waiting", "Housing Waiting List", "Seniority-ordered waiting list.", housing_waiting, ["category"]),
    Report("duty-roster", "Duty Roster", "Monthly duty roster.", duty_roster, ["year", "month"]),
    Report("transfers", "Transfer Log", "Inter-department transfer history.", transfers_log),
    Report("exits", "Exit & Archive Register", "Archived employees and housing vacation flags.", exits_register),
]
REPORTS_BY_KEY = {r.key: r for r in REPORTS}
