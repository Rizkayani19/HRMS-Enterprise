from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import (
    ContractExtension, DepartmentTransfer, Employee, EmploymentTypeChange, ExitRecord, FamilyMember,
    PreviousAppointment, Promotion,
)
from .validators import normalise_national_id, validate_national_id


class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        exclude = ["employee"]


class PreviousAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreviousAppointment
        exclude = ["employee"]


class TransferSerializer(serializers.ModelSerializer):
    from_department = serializers.CharField(source="from_department.name")
    to_department = serializers.CharField(source="to_department.name")

    class Meta:
        model = DepartmentTransfer
        exclude = ["employee"]


class PromotionSerializer(serializers.ModelSerializer):
    from_designation = serializers.CharField(source="from_designation.title")
    to_designation = serializers.CharField(source="to_designation.title")

    class Meta:
        model = Promotion
        exclude = ["employee"]


class ContractExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractExtension
        exclude = ["employee"]


class TypeChangeSerializer(serializers.ModelSerializer):
    from_type = serializers.CharField(source="from_type.name")
    to_type = serializers.CharField(source="to_type.name")

    class Meta:
        model = EmploymentTypeChange
        exclude = ["employee"]


class ExitRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitRecord
        exclude = ["employee"]


class EmployeeListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)
    grade = serializers.IntegerField(source="designation.grade", read_only=True)
    employment_type_name = serializers.CharField(source="employment_type.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, default="")

    class Meta:
        model = Employee
        fields = [
            "id", "employee_no", "full_name", "department", "department_name", "designation",
            "designation_title", "grade", "employment_type", "employment_type_name", "location_name",
            "status", "mobile", "office_ext", "email", "join_date", "contract_end",
        ]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_title = serializers.CharField(source="designation.title", read_only=True)
    grade = serializers.IntegerField(source="designation.grade", read_only=True)
    employment_type_name = serializers.CharField(source="employment_type.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, default="")
    retirement_date = serializers.DateField(read_only=True)
    years_of_service = serializers.FloatField(read_only=True)
    gross_pay = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    family = FamilyMemberSerializer(many=True, required=False)
    previous_appointments = PreviousAppointmentSerializer(many=True, required=False)
    transfers = TransferSerializer(many=True, read_only=True)
    promotions = PromotionSerializer(many=True, read_only=True)
    contract_extensions = ContractExtensionSerializer(many=True, read_only=True)
    type_changes = TypeChangeSerializer(many=True, read_only=True)
    exit_record = ExitRecordSerializer(read_only=True)
    housing = serializers.SerializerMethodField()
    national_id = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["status"]

    def get_housing(self, obj):
        a = obj.allotments.filter(vacated_on__isnull=True).select_related("unit").first()
        if a:
            return {"unit": a.unit.code, "block": a.unit.block, "occupied_from": a.occupied_from}
        entry = getattr(obj, "waiting_list_entry", None)
        if entry:
            return {"waiting_since": entry.registered_on, "category": entry.category}
        return None

    def validate_national_id(self, value):
        value = normalise_national_id(value)
        try:
            validate_national_id(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate(self, attrs):
        etype = attrs.get("employment_type") or getattr(self.instance, "employment_type", None)
        start = attrs.get("contract_start", getattr(self.instance, "contract_start", None))
        end = attrs.get("contract_end", getattr(self.instance, "contract_end", None))
        if etype and etype.is_contractual and not end:
            raise serializers.ValidationError({"contract_end": "Contract end date is required for contractual staff."})
        if start and end and end <= start:
            raise serializers.ValidationError({"contract_end": "Contract end must be after contract start."})
        return attrs

    def _write_children(self, emp, family, appointments):
        if family is not None:
            emp.family.all().delete()
            FamilyMember.objects.bulk_create(FamilyMember(employee=emp, **f) for f in family)
        if appointments is not None:
            emp.previous_appointments.all().delete()
            PreviousAppointment.objects.bulk_create(PreviousAppointment(employee=emp, **a) for a in appointments)

    @transaction.atomic
    def create(self, validated_data):
        family = validated_data.pop("family", None)
        appts = validated_data.pop("previous_appointments", None)
        emp = super().create(validated_data)
        self._write_children(emp, family, appts)
        return emp

    @transaction.atomic
    def update(self, instance, validated_data):
        family = validated_data.pop("family", None)
        appts = validated_data.pop("previous_appointments", None)
        emp = super().update(instance, validated_data)
        self._write_children(emp, family, appts)
        return emp
