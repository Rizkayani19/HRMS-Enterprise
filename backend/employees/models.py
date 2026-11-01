"""Employee master record and its lifecycle history."""
from datetime import date

from django.db import models

from masters.models import Department, Designation, EmploymentType, Location

from .validators import normalise_national_id, validate_mobile, validate_national_id

RETIREMENT_AGE = 60


class Employee(models.Model):
    STATUS_ACTIVE = "Active"
    STATUS_ON_LEAVE = "On Leave"
    STATUS_NOTICE = "Notice Period"
    STATUS_EXITED = "Exited"
    STATUS_CHOICES = [(s, s) for s in (STATUS_ACTIVE, STATUS_ON_LEAVE, STATUS_NOTICE, STATUS_EXITED)]
    GENDER_CHOICES = [("Male", "Male"), ("Female", "Female")]
    MARITAL_CHOICES = [("Single", "Single"), ("Married", "Married"), ("Widowed", "Widowed"), ("Divorced", "Divorced")]

    employee_no = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    father_name = models.CharField(max_length=150, blank=True, default="")
    national_id = models.CharField(max_length=13, blank=True, default="", validators=[validate_national_id])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="Male")
    dob = models.DateField("Date of birth", null=True, blank=True)
    blood_group = models.CharField(max_length=5, blank=True, default="")
    marital_status = models.CharField(max_length=10, choices=MARITAL_CHOICES, default="Single")
    mobile = models.CharField(max_length=11, blank=True, default="", validators=[validate_mobile])
    email = models.EmailField(blank=True, default="")
    office_ext = models.CharField("Office extension", max_length=6, blank=True, default="")
    address = models.TextField(blank=True, default="")
    home_district = models.CharField(max_length=60, blank=True, default="")
    qualification = models.CharField(max_length=120, blank=True, default="")

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name="employees")
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, related_name="employees")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="employees", null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    join_date = models.DateField()
    grade_seniority_date = models.DateField(null=True, blank=True, help_text="Date of seniority in current grade")
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    basic_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-designation__grade", "grade_seniority_date", "full_name"]

    def __str__(self):
        return f"{self.employee_no} - {self.full_name}"

    def save(self, *args, **kwargs):
        self.national_id = normalise_national_id(self.national_id)
        super().save(*args, **kwargs)

    @property
    def retirement_date(self):
        if not self.dob:
            return None
        try:
            return self.dob.replace(year=self.dob.year + RETIREMENT_AGE)
        except ValueError:  # 29 Feb
            return self.dob.replace(year=self.dob.year + RETIREMENT_AGE, day=28)

    @property
    def gross_pay(self):
        return self.basic_pay + self.allowances

    @property
    def years_of_service(self):
        end = date.today()
        return round((end - self.join_date).days / 365.25, 1)


class FamilyMember(models.Model):
    RELATION_CHOICES = [(r, r) for r in ("Spouse", "Son", "Daughter", "Father", "Mother")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="family")
    relationship = models.CharField(max_length=20, choices=RELATION_CHOICES)
    name = models.CharField(max_length=150)
    dob = models.DateField(null=True, blank=True)
    is_dependent = models.BooleanField(default=True)

    class Meta:
        ordering = ["employee", "relationship"]


class PreviousAppointment(models.Model):
    """Earlier appointments, inside or outside the organisation."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="previous_appointments")
    organisation = models.CharField(max_length=150)
    title = models.CharField(max_length=150)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["employee", "-from_date"]


class DepartmentTransfer(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="transfers")
    from_department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="+")
    to_department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="+")
    effective_date = models.DateField()
    order_ref = models.CharField(max_length=100, blank=True, default="")
    reason = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-id"]


class Promotion(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="promotions")
    from_designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name="+")
    to_designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name="+")
    effective_date = models.DateField()
    order_ref = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-id"]


class ContractExtension(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="contract_extensions")
    previous_end = models.DateField(null=True, blank=True)
    new_start = models.DateField()
    new_end = models.DateField()
    pay_revised = models.BooleanField(default=False)
    old_basic_pay = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_basic_pay = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    order_ref = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-new_start", "-id"]


class EmploymentTypeChange(models.Model):
    """Cadre conversion, e.g. Contract -> Permanent, without duplicating the profile."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="type_changes")
    from_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, related_name="+")
    to_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, related_name="+")
    effective_date = models.DateField()
    order_ref = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-id"]


class ExitRecord(models.Model):
    CATEGORY_CHOICES = [(c, c) for c in (
        "Resignation", "Retirement", "Contract Ended", "Transfer to Group Company", "Termination",
    )]
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="exit_record")
    exit_date = models.DateField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    destination = models.CharField(max_length=150, blank=True, default="")
    reliever = models.CharField(max_length=150, blank=True, default="")
    handover_notes = models.TextField(blank=True, default="")
    housing_vacation_due = models.BooleanField(default=False, help_text="Employee held staff housing at exit")
    created_at = models.DateTimeField(auto_now_add=True)
