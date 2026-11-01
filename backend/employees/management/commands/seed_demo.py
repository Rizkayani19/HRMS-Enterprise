"""Load the fictional NexGen Holdings Ltd. demo dataset.

Every name, ID number, phone number and figure here is randomly generated.
Usage:  python manage.py seed_demo [--reset] [--employees 80]
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import AuditLog
from accounts.permissions import ROLE_ADMIN, ROLE_OFFICER, ROLE_VIEWER
from duties.models import DutyAssignment, DutyType
from duties.services import generate_roster
from employees import services
from employees.models import Employee, FamilyMember, PreviousAppointment
from housing.models import Allotment, HousingUnit, WaitingListEntry
from masters.models import Department, Designation, EmploymentType, Location

FIRST_M = ["Ahmed", "Ali", "Hassan", "Usman", "Bilal", "Hamza", "Imran", "Kashif", "Faisal", "Saad", "Zain", "Omar",
           "Tariq", "Junaid", "Adnan", "Naveed", "Shahid", "Waqar", "Yasir", "Fahad", "Danish", "Rehan", "Asim", "Sohail"]
FIRST_F = ["Ayesha", "Fatima", "Sana", "Hina", "Maria", "Nida", "Saima", "Rabia", "Amna", "Zara", "Mehwish", "Sadia"]
LAST = ["Khan", "Siddiqui", "Qureshi", "Malik", "Sheikh", "Butt", "Chaudhry", "Hashmi", "Rana", "Mirza", "Baig",
        "Ansari", "Farooqi", "Javed", "Abbasi", "Rizvi", "Soomro", "Memon", "Lodhi", "Niazi"]
DISTRICTS = ["Karachi", "Lahore", "Hyderabad", "Multan", "Faisalabad", "Peshawar", "Quetta", "Sukkur", "Sialkot", "Abbottabad"]
QUALS = ["BBA", "MBA (HR)", "B.Com", "M.Com", "BS Computer Science", "MA Economics", "BSc", "Intermediate", "Matric",
         "ACCA", "LLB", "MSc Supply Chain"]

DEPARTMENTS = [("HR", "Human Resources"), ("FIN", "Finance & Accounts"), ("ADM", "Administration"),
               ("OPS", "Operations"), ("SEC", "Security"), ("IT", "Information Technology"),
               ("PRC", "Procurement & Stores"), ("LGL", "Legal & Compliance"), ("TRN", "Transport")]
DESIGNATIONS = [("Chief Executive Officer", 20, "Executive"), ("Director", 18, "Executive"),
                ("General Manager", 17, "Manager"), ("Deputy General Manager", 16, "Manager"),
                ("Manager", 15, "Manager"), ("Assistant Manager", 13, "Officer"), ("Senior Officer", 12, "Officer"),
                ("Officer", 11, "Officer"), ("Senior Assistant", 9, "Staff"), ("Assistant", 8, "Staff"),
                ("Data Entry Operator", 7, "Staff"), ("Driver", 5, "Support"), ("Security Guard", 4, "Support"),
                ("Office Attendant", 3, "Support")]
TYPES = [("Permanent", False), ("Contract", True), ("Probation", False), ("Re-employed Retiree", True)]
LOCATIONS = [("Head Office", "Karachi"), ("Regional Office", "Lahore"), ("Liaison Office", "Islamabad"),
             ("Central Warehouse", "Port Qasim")]
PAY_BY_GRADE = {20: 900000, 18: 600000, 17: 450000, 16: 380000, 15: 300000, 13: 200000, 12: 160000, 11: 130000,
                9: 90000, 8: 75000, 7: 65000, 5: 50000, 4: 45000, 3: 40000}
# How many of each designation (by grade) to create, roughly.
SHAPE = {20: 1, 18: 3, 17: 5, 16: 6, 15: 9, 13: 10, 12: 10, 11: 10, 9: 8, 8: 8, 7: 6, 5: 6, 4: 8, 3: 6}


class Command(BaseCommand):
    help = "Load the synthetic NexGen Holdings demo dataset."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing HR data first")
        parser.add_argument("--seed", type=int, default=19)

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])
        if opts["reset"]:
            for m in (DutyAssignment, DutyType, Allotment, WaitingListEntry, HousingUnit, Employee, AuditLog,
                      Department, Designation, EmploymentType, Location):
                m.objects.all().delete()
        if Employee.objects.exists():
            self.stdout.write(self.style.WARNING("Data already present - use --reset to reload."))
            return

        today = date.today()
        depts = {c: Department.objects.create(code=c, name=n) for c, n in DEPARTMENTS}
        desigs = {g: Designation.objects.create(title=t, grade=g, category=cat) for t, g, cat in DESIGNATIONS}
        types = {n: EmploymentType.objects.create(name=n, is_contractual=c) for n, c in TYPES}
        locs = [Location.objects.create(name=n, city=c) for n, c in LOCATIONS]
        admin_user = self._users()

        def rand_date(start, end):
            return start + timedelta(days=rnd.randint(0, max((end - start).days, 0)))

        used_ids = set()

        def fake_nid():
            while True:
                v = "9" + "".join(str(rnd.randint(0, 9)) for _ in range(12))
                if v not in used_ids:
                    used_ids.add(v)
                    return v

        employees, n, used_names = [], 0, set()
        for grade, count in SHAPE.items():
            for _ in range(count):
                n += 1
                female = rnd.random() < 0.22 and grade >= 7
                while True:
                    first = rnd.choice(FIRST_F if female else FIRST_M)
                    last = rnd.choice(LAST)
                    if (first, last) not in used_names:
                        used_names.add((first, last))
                        break
                age = rnd.randint(24, 40) + (grade // 2) if grade < 18 else rnd.randint(50, 59)
                age = min(age, 59)
                dob = rand_date(today - timedelta(days=365 * (age + 1)), today - timedelta(days=365 * age))
                join = rand_date(dob + timedelta(days=365 * 22), today - timedelta(days=60))
                if grade == 20:
                    dept = depts["ADM"]
                elif grade <= 5:
                    dept = depts[{5: "TRN", 4: "SEC", 3: "ADM"}[grade]]
                else:
                    dept = rnd.choice(list(depts.values()))
                if age >= 58 and rnd.random() < 0.5:
                    etype = types["Re-employed Retiree"]
                else:
                    etype = rnd.choices([types["Permanent"], types["Contract"], types["Probation"]], [65, 28, 7])[0]
                c_start = c_end = None
                if etype.is_contractual:
                    c_start = rand_date(today - timedelta(days=700), today - timedelta(days=30))
                    c_end = c_start + timedelta(days=rnd.choice([365, 730]))
                    if rnd.random() < 0.3:
                        c_end = today + timedelta(days=rnd.randint(5, 85))
                base = PAY_BY_GRADE[grade]
                e = Employee.objects.create(
                    employee_no=f"NX-{1000 + n}", full_name=f"{first} {last}",
                    father_name=f"{rnd.choice(FIRST_M)} {last}", national_id=fake_nid(),
                    gender="Female" if female else "Male", dob=dob,
                    blood_group=rnd.choice(["A+", "B+", "O+", "AB+", "A-", "B-", "O-"]),
                    marital_status="Married" if age > 28 and rnd.random() < 0.8 else "Single",
                    mobile="03" + "".join(str(rnd.randint(0, 9)) for _ in range(9)),
                    email=f"{first.lower()}.{last.lower()}{n}@nexgen.example",
                    office_ext=str(2000 + n), home_district=rnd.choice(DISTRICTS),
                    address=f"House {rnd.randint(1, 300)}, Street {rnd.randint(1, 40)}, {rnd.choice(DISTRICTS)}",
                    qualification=rnd.choice(QUALS), department=dept, designation=desigs[grade],
                    employment_type=etype, location=locs[0] if rnd.random() < 0.7 else rnd.choice(locs[1:]),
                    join_date=join, grade_seniority_date=rand_date(join, today - timedelta(days=30)),
                    contract_start=c_start, contract_end=c_end,
                    basic_pay=Decimal(round(base * rnd.uniform(0.9, 1.1), -2)),
                    allowances=Decimal(round(base * rnd.uniform(0.25, 0.45), -2)),
                )
                if e.marital_status == "Married":
                    FamilyMember.objects.create(employee=e, relationship="Spouse",
                                                name=f"{rnd.choice(FIRST_M if female else FIRST_F)} {last}")
                    for _ in range(rnd.randint(0, 3)):
                        rel = rnd.choice(["Son", "Daughter"])
                        FamilyMember.objects.create(
                            employee=e, relationship=rel,
                            name=f"{rnd.choice(FIRST_M if rel == 'Son' else FIRST_F)} {last}",
                            dob=rand_date(join, today - timedelta(days=200)))
                if grade >= 11 and rnd.random() < 0.6:
                    end = join - timedelta(days=rnd.randint(15, 120))
                    PreviousAppointment.objects.create(
                        employee=e, organisation=rnd.choice(["Orion Textiles", "Delta Logistics", "Crescent Foods",
                                                             "Summit Bank", "Apex Engineering"]),
                        title=rnd.choice(["Officer", "Assistant Manager", "Executive", "Coordinator"]),
                        from_date=end - timedelta(days=rnd.randint(400, 2000)), to_date=end)
                employees.append(e)

        # Two senior staff close to retirement, so the dashboard has something to show.
        for e, months in zip([x for x in employees if x.designation.grade in (16, 17)][:2], (4, 9)):
            r = today + timedelta(days=months * 30)
            e.dob = r.replace(year=r.year - 60)
            e.save()

        # A few on leave / notice.
        for e in rnd.sample(employees, 4):
            e.status = Employee.STATUS_ON_LEAVE
            e.save()
        for e in rnd.sample([x for x in employees if x.status == "Active"], 2):
            e.status = Employee.STATUS_NOTICE
            e.save()

        # History through the real lifecycle services so the audit log is realistic.
        for e in rnd.sample(employees, 8):
            to = rnd.choice([d for d in depts.values() if d != e.department])
            services.transfer(e, to, today - timedelta(days=rnd.randint(10, 300)), user=admin_user,
                              order_ref=f"HR/TRF/{rnd.randint(100, 999)}", reason="Organisational requirement")
        for e in rnd.sample([x for x in employees if x.designation.grade in (11, 12, 13)], 4):
            nxt = Designation.objects.filter(grade__gt=e.designation.grade).order_by("grade").first()
            services.promote(e, nxt, today - timedelta(days=rnd.randint(20, 200)), user=admin_user,
                             order_ref=f"HR/PRM/{rnd.randint(100, 999)}")
        contractual = [x for x in employees if x.employment_type.is_contractual and x.contract_end
                       and x.contract_end <= today + timedelta(days=40)]
        for e in rnd.sample(contractual, min(3, len(contractual))):
            services.extend_contract(e, e.contract_end + timedelta(days=365), user=admin_user,
                                     new_basic_pay=(e.basic_pay * Decimal("1.10")).quantize(Decimal("1")),
                                     order_ref=f"HR/EXT/{rnd.randint(100, 999)}")
        probation = [x for x in employees if x.employment_type.name == "Probation"]
        for e in probation[:2]:
            services.change_employment_type(e, types["Permanent"], today - timedelta(days=rnd.randint(5, 60)),
                                            user=admin_user, order_ref=f"HR/CNF/{rnd.randint(100, 999)}")

        # Housing.
        units = []
        for i in range(1, 13):
            units.append(HousingUnit.objects.create(code=f"A-{i:02d}", block="Block A, Staff Colony",
                                                    category="Family Flat", min_grade=11))
        for i in range(1, 7):
            units.append(HousingUnit.objects.create(code=f"B-{i:02d}", block="Block B, Staff Colony",
                                                    category="Family House", min_grade=15))
        for i in range(1, 11):
            units.append(HousingUnit.objects.create(code=f"H-{i:02d}", block="Staff Hostel",
                                                    category="Bachelor Room", min_grade=3))
        units[-1].is_serviceable = False
        units[-1].save()
        pool = [e for e in employees if e.status != "Exited"]
        rnd.shuffle(pool)
        for u in units:
            if not u.is_serviceable or (u.category == "Bachelor Room" and rnd.random() < 0.3):
                continue
            want_single = u.category == "Bachelor Room"
            cand = next((e for e in pool if e.designation.grade >= u.min_grade
                         and (e.marital_status == "Single") == want_single
                         and not Allotment.objects.filter(employee=e, vacated_on__isnull=True).exists()), None)
            if cand:
                Allotment.objects.create(unit=u, employee=cand,
                                         occupied_from=rand_date(cand.join_date, today - timedelta(days=10)))
                pool.remove(cand)
        vacant_houses = any(u.current_allotment is None and u.is_serviceable for u in units if u.category == "Family House")
        waiting = [x for x in pool if x.marital_status == "Married" and 11 <= x.designation.grade < 15]
        if not vacant_houses:
            waiting += [x for x in pool if x.marital_status == "Married" and x.designation.grade >= 15]
        for e in waiting[:10]:
            WaitingListEntry.objects.create(employee=e, category="Family House" if e.designation.grade >= 15 else "Family Flat",
                                            registered_on=rand_date(e.join_date, today - timedelta(days=5)))

        # Exits (one of them holding housing, to show the vacation flag).
        housed = Allotment.objects.filter(vacated_on__isnull=True).select_related("employee").first()
        leavers = [housed.employee] + rnd.sample([e for e in employees if e != housed.employee and e.designation.grade < 18], 3)
        cats = ["Transfer to Group Company", "Resignation", "Retirement", "Contract Ended"]
        for e, cat in zip(leavers, cats):
            e.refresh_from_db()
            services.exit_employee(e, today - timedelta(days=rnd.randint(3, 120)), cat, user=admin_user,
                                   destination="NexGen Energy Ltd." if cat.startswith("Transfer") else "",
                                   reliever="Awaited", handover_notes="Handover completed.")

        # Duties.
        DutyType.objects.create(name="Weekend Duty Manager", min_grade=13, max_grade=17, weekends_only=True)
        DutyType.objects.create(name="Night Duty Officer", min_grade=11, max_grade=13)
        DutyType.objects.create(name="Security Supervisor", min_grade=4, max_grade=9)
        prev = today.replace(day=1) - timedelta(days=1)
        generate_roster(prev.year, prev.month, user=admin_user)
        generate_roster(today.year, today.month, user=admin_user)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Employee.objects.count()} employees, {HousingUnit.objects.count()} housing units, "
            f"{DutyAssignment.objects.count()} duties."))

    def _users(self):
        groups = {r: Group.objects.get_or_create(name=r)[0] for r in (ROLE_ADMIN, ROLE_OFFICER, ROLE_VIEWER)}
        created = None
        for username, pw, role, name in (("admin", "admin123", ROLE_ADMIN, "Demo Administrator"),
                                         ("hrofficer", "officer123", ROLE_OFFICER, "Demo HR Officer"),
                                         ("viewer", "viewer123", ROLE_VIEWER, "Demo Viewer")):
            u, _ = User.objects.get_or_create(username=username, defaults={"first_name": name})
            u.set_password(pw)
            u.is_staff = role == ROLE_ADMIN
            u.is_superuser = role == ROLE_ADMIN
            u.save()
            u.groups.set([groups[role]])
            if role == ROLE_ADMIN:
                created = u
        return created
