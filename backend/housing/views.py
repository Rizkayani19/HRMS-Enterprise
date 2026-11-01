from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from employees.models import Employee

from . import services
from .models import HousingUnit, WaitingListEntry


class HousingUnitSerializer(serializers.ModelSerializer):
    occupant = serializers.SerializerMethodField()

    class Meta:
        model = HousingUnit
        fields = "__all__"

    def get_occupant(self, obj):
        a = obj.current_allotment
        if not a:
            return None
        return {"employee_id": a.employee_id, "employee_no": a.employee.employee_no,
                "full_name": a.employee.full_name, "occupied_from": a.occupied_from}


class WaitingListSerializer(serializers.ModelSerializer):
    employee_no = serializers.CharField(source="employee.employee_no", read_only=True)
    full_name = serializers.CharField(source="employee.full_name", read_only=True)
    designation = serializers.CharField(source="employee.designation.title", read_only=True)
    grade = serializers.IntegerField(source="employee.designation.grade", read_only=True)
    department = serializers.CharField(source="employee.department.name", read_only=True)

    class Meta:
        model = WaitingListEntry
        fields = "__all__"


class _AllotIn(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    occupied_from = serializers.DateField()


class _VacateIn(serializers.Serializer):
    vacated_on = serializers.DateField()


class HousingUnitViewSet(viewsets.ModelViewSet):
    queryset = HousingUnit.objects.all()
    serializer_class = HousingUnitSerializer

    @action(detail=True, methods=["post"])
    def allot(self, request, pk=None):
        s = _AllotIn(data=request.data)
        s.is_valid(raise_exception=True)
        unit = self.get_object()
        services.allot(unit, s.validated_data["employee"], s.validated_data["occupied_from"], user=request.user)
        return Response(HousingUnitSerializer(unit).data)

    @action(detail=True, methods=["post"])
    def vacate(self, request, pk=None):
        s = _VacateIn(data=request.data)
        s.is_valid(raise_exception=True)
        unit = self.get_object()
        services.vacate(unit, s.validated_data["vacated_on"], user=request.user)
        return Response(HousingUnitSerializer(unit).data)


class WaitingListViewSet(viewsets.ModelViewSet):
    serializer_class = WaitingListSerializer

    def get_queryset(self):
        qs = WaitingListEntry.objects.select_related("employee__designation", "employee__department")
        if cat := self.request.query_params.get("category"):
            qs = qs.filter(category=cat)
        return qs.order_by("registered_on", "employee__employee_no")
