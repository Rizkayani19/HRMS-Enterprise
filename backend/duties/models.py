"""Duty types and a fair, rotating duty roster."""
from django.db import models

from employees.models import Employee


class DutyType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    min_grade = models.PositiveSmallIntegerField(default=1)
    max_grade = models.PositiveSmallIntegerField(default=20)
    weekends_only = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DutyAssignment(models.Model):
    duty_type = models.ForeignKey(DutyType, on_delete=models.CASCADE, related_name="assignments")
    date = models.DateField()
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="duties")

    class Meta:
        ordering = ["date", "duty_type__name"]
        constraints = [models.UniqueConstraint(fields=["duty_type", "date"], name="one_person_per_duty_per_day")]
