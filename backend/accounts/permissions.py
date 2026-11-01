"""Three roles, mapped to Django groups:

* HR Admin   - everything, including master data and user management
* HR Officer - create/edit employees and run lifecycle actions
* Viewer     - read-only access and reports
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

ROLE_ADMIN = "HR Admin"
ROLE_OFFICER = "HR Officer"
ROLE_VIEWER = "Viewer"


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROLE_ADMIN
    names = set(user.groups.values_list("name", flat=True))
    for role in (ROLE_ADMIN, ROLE_OFFICER, ROLE_VIEWER):
        if role in names:
            return role
    return ROLE_VIEWER


class RoleBasedPermission(BasePermission):
    """Read for any signed-in user; write for HR Officer and HR Admin.

    Views can set `admin_only_write = True` to restrict writes to HR Admin.
    """

    def has_permission(self, request, view):
        role = user_role(request.user)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        if getattr(view, "admin_only_write", False):
            return role == ROLE_ADMIN
        return role in (ROLE_ADMIN, ROLE_OFFICER)
