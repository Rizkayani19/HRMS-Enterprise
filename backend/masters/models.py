"""Controlled master data (lookup tables) used across the HRMS."""
from django.db import models


class Department(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Designation(models.Model):
    CATEGORY_CHOICES = [
        ("Executive", "Executive"),
        ("Manager", "Manager"),
        ("Officer", "Officer"),
        ("Staff", "Staff"),
        ("Support", "Support"),
    ]
    title = models.CharField(max_length=120, unique=True)
    grade = models.PositiveSmallIntegerField(help_text="Pay grade, 1 (lowest) to 20 (highest)")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    class Meta:
        ordering = ["-grade", "title"]

    def __str__(self):
        return f"{self.title} (G-{self.grade})"


class EmploymentType(models.Model):
    name = models.CharField(max_length=60, unique=True)
    is_contractual = models.BooleanField(default=False, help_text="Requires contract start/end dates")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=120, unique=True)
    city = models.CharField(max_length=60)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.city}"
