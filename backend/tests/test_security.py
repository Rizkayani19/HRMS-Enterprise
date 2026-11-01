import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured
from rest_framework.test import APIClient


def test_anonymous_is_rejected(db):
    assert APIClient().get("/api/employees/").status_code == 403


def test_viewer_is_read_only(viewer_client, make_employee, masters):
    e = make_employee()
    assert viewer_client.get("/api/employees/").status_code == 200
    assert viewer_client.patch(f"/api/employees/{e.id}/", {"full_name": "X"}, format="json").status_code == 403
    assert viewer_client.post(f"/api/employees/{e.id}/exit/", {}, format="json").status_code == 403


def test_master_data_is_admin_only(officer_client, admin_client):
    body = {"code": "NEW", "name": "New Dept"}
    assert officer_client.post("/api/departments/", body, format="json").status_code == 403
    assert admin_client.post("/api/departments/", body, format="json").status_code == 201


def test_login_flow(db):
    from django.contrib.auth.models import User
    User.objects.create_user("u1", password="secret-pass")
    c = APIClient(enforce_csrf_checks=False)
    assert c.post("/api/auth/login/", {"username": "u1", "password": "wrong"}, format="json").status_code == 400
    r = c.post("/api/auth/login/", {"username": "u1", "password": "secret-pass"}, format="json")
    assert r.status_code == 200 and r.data["role"] == "Viewer"
    assert c.get("/api/auth/me/").data["username"] == "u1"


def test_production_requires_secret_key(monkeypatch):
    import config.settings as s
    monkeypatch.setenv("DJANGO_DEBUG", "False")
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    with pytest.raises(ImproperlyConfigured):
        importlib.reload(s)
    monkeypatch.setenv("DJANGO_DEBUG", "True")
    importlib.reload(s)


def test_postgres_requires_password(monkeypatch):
    import config.settings as s
    monkeypatch.setenv("HRMS_DB_ENGINE", "postgres")
    monkeypatch.delenv("HRMS_DB_PASSWORD", raising=False)
    with pytest.raises(ImproperlyConfigured):
        importlib.reload(s)
    monkeypatch.setenv("HRMS_DB_ENGINE", "sqlite")
    importlib.reload(s)


def test_backup_command_sqlite(tmp_path, settings, db):
    from django.core.management import call_command
    src = tmp_path / "src.sqlite3"
    src.write_bytes(b"SQLite format 3\x00")
    settings.DATABASES["default"]["NAME"] = src
    call_command("backup_db", dir=str(tmp_path / "bk"))
    assert len(list((tmp_path / "bk").glob("hrms_*.sqlite3"))) == 1
