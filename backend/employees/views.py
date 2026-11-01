import csv
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog
from housing.models import Allotment, HousingUnit, WaitingListEntry
from masters.models import Department, Designation, EmploymentType

from . import services
from .models import Employee, ExitRecord
from .serializers import EmployeeDetailSerializer, EmployeeListSerializer


class _TransferIn(serializers.Serializer):
    to_department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    effective_date = serializers.DateField()
    order_ref = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class _PromoteIn(serializers.Serializer):
    to_designation = serializers.PrimaryKeyRelatedField(queryset=Designation.objects.all())
    effective_date = serializers.DateField()
    order_ref = serializers.CharField(required=False, allow_blank=True, default="")
    new_basic_pay = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


class _ExtendIn(serializers.Serializer):
    new_end = serializers.DateField()
    new_start = serializers.DateField(required=False, allow_null=True)
    new_basic_pay = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    order_ref = serializers.CharField(required=False, allow_blank=True, default="")


class _TypeChangeIn(serializers.Serializer):
    to_type = serializers.PrimaryKeyRelatedField(queryset=EmploymentType.objects.all())
    effective_date = serializers.DateField()
    contract_end = serializers.DateField(required=False, allow_null=True)
    order_ref = serializers.CharField(required=False, allow_blank=True, default="")


class _ExitIn(serializers.Serializer):
    exit_date = serializers.DateField()
    category = serializers.ChoiceField(choices=ExitRecord.CATEGORY_CHOICES)
    destination = serializers.CharField(required=False, allow_blank=True, default="")
    reliever = serializers.CharField(required=False, allow_blank=True, default="")
    handover_notes = serializers.CharField(required=False, allow_blank=True, default="")


class _BulkIn(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    action = serializers.ChoiceField(choices=["status", "transfer"])
    status = serializers.ChoiceField(choices=Employee.STATUS_CHOICES, required=False)
    to_department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False)
    effective_date = serializers.DateField(required=False)
    order_ref = serializers.CharField(required=False, allow_blank=True, default="")


def filter_employees(params, qs=None):
    qs = qs if qs is not None else Employee.objects.all()
    qs = qs.select_related("department", "designation", "employment_type", "location")
    archived = params.get("archived") in ("1", "true")
    qs = qs.filter(status=Employee.STATUS_EXITED) if archived else qs.exclude(status=Employee.STATUS_EXITED)
    if q := params.get("q"):
        qs = qs.filter(
            Q(full_name__icontains=q) | Q(employee_no__icontains=q) | Q(national_id__icontains=q)
            | Q(mobile__icontains=q) | Q(designation__title__icontains=q)
        )
    for key, field in (("department", "department_id"), ("designation", "designation_id"),
                       ("employment_type", "employment_type_id"), ("status", "status")):
        if val := params.get(key):
            qs = qs.filter(**{field: val})
    return qs


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()

    def get_serializer_class(self):
        return EmployeeListSerializer if self.action == "list" else EmployeeDetailSerializer

    def get_queryset(self):
        if self.action == "list":
            return filter_employees(self.request.query_params)
        return Employee.objects.select_related("department", "designation", "employment_type", "location")

    def perform_create(self, serializer):
        emp = serializer.save()
        AuditLog.record(self.request.user, "create", f"{emp.employee_no}: {emp.full_name}")

    def perform_update(self, serializer):
        emp = serializer.save()
        AuditLog.record(self.request.user, "update", emp.employee_no)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Employees are archived through the exit action, not deleted."},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def _run(self, request, in_serializer, fn):
        s = in_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        emp = self.get_object()
        fn(emp, user=request.user, **s.validated_data)
        emp.refresh_from_db()
        return Response(EmployeeDetailSerializer(emp).data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        return self._run(request, _TransferIn, services.transfer)

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        return self._run(request, _PromoteIn, services.promote)

    @action(detail=True, methods=["post"], url_path="extend-contract")
    def extend_contract(self, request, pk=None):
        return self._run(request, _ExtendIn, services.extend_contract)

    @action(detail=True, methods=["post"], url_path="change-type")
    def change_type(self, request, pk=None):
        return self._run(request, _TypeChangeIn, services.change_employment_type)

    @action(detail=True, methods=["post"], url_path="exit")
    def exit(self, request, pk=None):
        return self._run(request, _ExitIn, services.exit_employee)

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        s = _BulkIn(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        emps = list(Employee.objects.filter(id__in=d["ids"]))
        if d["action"] == "status":
            if not d.get("status"):
                raise serializers.ValidationError({"status": "Required."})
            n = services.bulk_update_status(emps, d["status"], user=request.user)
        else:
            if not d.get("to_department") or not d.get("effective_date"):
                raise serializers.ValidationError({"to_department": "Department and effective date are required."})
            n = services.bulk_transfer(emps, d["to_department"], d["effective_date"], user=request.user,
                                       order_ref=d.get("order_ref", ""))
        return Response({"updated": n})

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        qs = filter_employees(request.query_params)
        if ids := request.query_params.get("ids"):
            qs = qs.filter(id__in=[int(i) for i in ids.split(",") if i.isdigit()])
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="employees.csv"'
        w = csv.writer(resp)
        w.writerow(["Employee No", "Name", "Designation", "Grade", "Department", "Employment Type",
                    "Status", "Join Date", "Contract End", "Mobile", "Ext", "Email"])
        for e in qs:
            w.writerow([e.employee_no, e.full_name, e.designation.title, e.designation.grade, e.department.name,
                        e.employment_type.name, e.status, e.join_date, e.contract_end or "", e.mobile,
                        e.office_ext, e.email])
        return resp


class DashboardView(APIView):
    def get(self, request):
        today = date.today()
        active = Employee.objects.exclude(status=Employee.STATUS_EXITED)
        by_dept = list(active.values("department__name").annotate(n=Count("id")).order_by("-n"))
        by_type = list(active.values("employment_type__name").annotate(n=Count("id")).order_by("-n"))
        by_cat = list(active.values("designation__category").annotate(n=Count("id")).order_by("-n"))
        contracts_due = active.filter(contract_end__gte=today, contract_end__lte=today + timedelta(days=90))
        retiring = [e for e in active.exclude(dob=None) if e.retirement_date and today <= e.retirement_date <= today + timedelta(days=365)]
        units = HousingUnit.objects.filter(is_serviceable=True)
        occupied = Allotment.objects.filter(vacated_on__isnull=True).count()
        return Response({
            "org_name": settings.HRMS_ORG_NAME,
            "headcount": active.count(),
            "on_leave": active.filter(status=Employee.STATUS_ON_LEAVE).count(),
            "notice_period": active.filter(status=Employee.STATUS_NOTICE).count(),
            "exited_this_year": ExitRecord.objects.filter(exit_date__year=today.year).count(),
            "by_department": [{"label": r["department__name"], "value": r["n"]} for r in by_dept],
            "by_type": [{"label": r["employment_type__name"], "value": r["n"]} for r in by_type],
            "by_category": [{"label": r["designation__category"], "value": r["n"]} for r in by_cat],
            "contracts_due": EmployeeListSerializer(contracts_due.order_by("contract_end"), many=True).data,
            "retiring": [{"id": e.id, "employee_no": e.employee_no, "full_name": e.full_name,
                          "retirement_date": e.retirement_date} for e in sorted(retiring, key=lambda e: e.retirement_date)],
            "housing": {"units": units.count(), "occupied": occupied,
                        "waiting": WaitingListEntry.objects.count()},
            "recent_activity": [
                {"action": a.action, "detail": a.detail, "at": a.created_at,
                 "user": a.user.username if a.user else "system"}
                for a in AuditLog.objects.select_related("user")[:8]
            ],
        })
