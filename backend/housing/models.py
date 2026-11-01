"""Staff housing inventory, allotments and a seniority-based waiting list."""
from django.db import models

from employees.models import Employee


class HousingUnit(models.Model):
    CATEGORY_CHOICES = [(c, c) for c in ("Family Flat", "Family House", "Bachelor Room")]
    code = models.CharField(max_length=20, unique=True)
    block = models.CharField(max_length=60)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    min_grade = models.PositiveSmallIntegerField(default=1, help_text="Minimum pay grade entitled")
    is_serviceable = models.BooleanField(default=True)

    class Meta:
        ordering = ["block", "code"]

    def __str__(self):
        return f"{self.code} ({self.block})"

    @property
    def current_allotment(self):
        return self.allotments.filter(vacated_on__isnull=True).select_related("employee").first()


class Allotment(models.Model):
    unit = models.ForeignKey(HousingUnit, on_delete=models.PROTECT, related_name="allotments")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="allotments")
    occupied_from = models.DateField()
    vacated_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-occupied_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["unit"], condition=models.Q(vacated_on__isnull=True), name="one_occupant_per_unit"
            ),
            models.UniqueConstraint(
                fields=["employee"], condition=models.Q(vacated_on__isnull=True), name="one_unit_per_employee"
            ),
        ]


class WaitingListEntry(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="waiting_list_entry")
    category = models.CharField(max_length=20, choices=HousingUnit.CATEGORY_CHOICES)
    registered_on = models.DateField(help_text="Seniority on the list is counted from this date")
    remarks = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["registered_on", "employee__employee_no"]
