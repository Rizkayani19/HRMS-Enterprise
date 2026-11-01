from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from accounts import views as acc
from duties.views import DutyAssignmentViewSet, DutyTypeViewSet
from employees.views import DashboardView, EmployeeViewSet
from housing.views import HousingUnitViewSet, WaitingListViewSet
from masters import views as m
from reports.views import ReportListView, ReportView

router = DefaultRouter()
router.register("departments", m.DepartmentViewSet)
router.register("designations", m.DesignationViewSet)
router.register("employment-types", m.EmploymentTypeViewSet)
router.register("locations", m.LocationViewSet)
router.register("employees", EmployeeViewSet)
router.register("housing/units", HousingUnitViewSet)
router.register("housing/waiting-list", WaitingListViewSet, basename="waiting-list")
router.register("duty-types", DutyTypeViewSet)
router.register("duties", DutyAssignmentViewSet, basename="duties")

api = [
    path("auth/csrf/", acc.CsrfView.as_view()),
    path("auth/login/", acc.LoginView.as_view()),
    path("auth/logout/", acc.LogoutView.as_view()),
    path("auth/me/", acc.MeView.as_view()),
    path("audit-log/", acc.AuditLogView.as_view()),
    path("dashboard/", DashboardView.as_view()),
    path("reports/", ReportListView.as_view()),
    path("reports/<slug:key>/", ReportView.as_view()),
    path("reports/<slug:key>/<str:fmt>/", ReportView.as_view()),
    path("", include(router.urls)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api)),
]

if (settings.FRONTEND_DIST / "index.html").exists():
    # Serve the built React app for every non-API route.
    urlpatterns.append(re_path(r"^(?!api/|admin/|static/).*$", TemplateView.as_view(template_name="index.html")))
