from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DutyAssignment, DutyType
from .services import generate_roster


class DutyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DutyType
        fields = "__all__"


class DutyAssignmentSerializer(serializers.ModelSerializer):
    duty_name = serializers.CharField(source="duty_type.name", read_only=True)
    employee_no = serializers.CharField(source="employee.employee_no", read_only=True)
    full_name = serializers.CharField(source="employee.full_name", read_only=True)
    designation = serializers.CharField(source="employee.designation.title", read_only=True)

    class Meta:
        model = DutyAssignment
        fields = "__all__"


class _GenerateIn(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    replace = serializers.BooleanField(default=False)


class DutyTypeViewSet(viewsets.ModelViewSet):
    queryset = DutyType.objects.all()
    serializer_class = DutyTypeSerializer
    admin_only_write = True


class DutyAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = DutyAssignmentSerializer

    def get_queryset(self):
        qs = DutyAssignment.objects.select_related("duty_type", "employee__designation")
        p = self.request.query_params
        if p.get("year") and p.get("month"):
            qs = qs.filter(date__year=p["year"], date__month=p["month"])
        return qs

    @action(detail=False, methods=["post"])
    def generate(self, request):
        s = _GenerateIn(data=request.data)
        s.is_valid(raise_exception=True)
        n = generate_roster(user=request.user, **s.validated_data)
        return Response({"created": n})
