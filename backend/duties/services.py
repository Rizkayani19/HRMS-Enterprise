"""Fair rotating duty roster.

Works day by day. For each duty, picks the eligible employee (right grade band, active,
not already on duty that day) with the fewest duties overall, then the fewest of that
duty type, then whoever did it least recently.
"""
import calendar
from collections import defaultdict
from datetime import date

from django.db import transaction

from accounts.models import AuditLog
from employees.models import Employee

from .models import DutyAssignment, DutyType


@transaction.atomic
def generate_roster(year: int, month: int, duty_types=None, user=None, replace=False):
    duty_types = list(duty_types or DutyType.objects.all())
    days = [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)]
    if replace:
        DutyAssignment.objects.filter(date__in=days, duty_type__in=duty_types).delete()

    type_count, total, last = defaultdict(int), defaultdict(int), {}
    for a in DutyAssignment.objects.values("duty_type_id", "employee_id", "date"):
        type_count[(a["duty_type_id"], a["employee_id"])] += 1
        total[a["employee_id"]] += 1
        key = (a["duty_type_id"], a["employee_id"])
        last[key] = max(last.get(key, date.min), a["date"])

    busy = defaultdict(set)
    taken = set()
    for a in DutyAssignment.objects.filter(date__in=days).values("date", "employee_id", "duty_type_id"):
        busy[a["date"]].add(a["employee_id"])
        taken.add((a["duty_type_id"], a["date"]))

    pools = {
        dt.id: list(Employee.objects.filter(status=Employee.STATUS_ACTIVE, designation__grade__gte=dt.min_grade,
                                            designation__grade__lte=dt.max_grade).order_by("employee_no"))
        for dt in duty_types
    }

    created = 0
    for day in days:
        for dt in duty_types:
            if (dt.id, day) in taken or (dt.weekends_only and day.weekday() < 5):
                continue
            candidates = [e for e in pools[dt.id] if e.id not in busy[day]]
            if not candidates:
                continue
            pick = min(candidates, key=lambda e: (total[e.id], type_count[(dt.id, e.id)],
                                                  last.get((dt.id, e.id), date.min), e.employee_no))
            DutyAssignment.objects.create(duty_type=dt, date=day, employee=pick)
            total[pick.id] += 1
            type_count[(dt.id, pick.id)] += 1
            last[(dt.id, pick.id)] = day
            busy[day].add(pick.id)
            created += 1
    AuditLog.record(user, "roster", f"{created} duties generated for {year}-{month:02d}")
    return created
