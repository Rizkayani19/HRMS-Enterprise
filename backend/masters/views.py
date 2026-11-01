from rest_framework import viewsets

from .models import Department, Designation, EmploymentType, Location
from .serializers import DepartmentSerializer, DesignationSerializer, EmploymentTypeSerializer, LocationSerializer


class _MasterViewSet(viewsets.ModelViewSet):
    admin_only_write = True


class DepartmentViewSet(_MasterViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class DesignationViewSet(_MasterViewSet):
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer


class EmploymentTypeViewSet(_MasterViewSet):
    queryset = EmploymentType.objects.all()
    serializer_class = EmploymentTypeSerializer


class LocationViewSet(_MasterViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
