from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Who did what, and when, for every lifecycle and bulk action."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=60)
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def record(cls, user, action, detail=""):
        return cls.objects.create(user=user if user and user.is_authenticated else None, action=action, detail=detail)
