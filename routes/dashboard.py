"""Các trang giao diện (render Jinja2). Quyền xem trang lấy từ config.NAV; dữ liệu lấy qua /api/*."""
from flask import Blueprint, abort, redirect, render_template

import config as C
from services.auth_service import current_user
from services.data_manager import db
from utils.decorators import login_required, roles_required

bp = Blueprint("pages", __name__)
STAFF = ("ADMIN", "MANAGER")


@bp.get("/")
def index():
    return redirect("/dashboard" if current_user() else "/login")


@bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", page="dashboard", title="Tổng quan")


@bp.get("/me")
@roles_required("LECTURER")
def my_profile():
    lid = current_user().get("lecturer_id")
    return redirect(f"/lecturers/{lid}") if lid else render_template("403.html"), (302 if lid else 403)


@bp.get("/lecturers")
@roles_required(*STAFF)
def lecturers():
    return render_template("lecturers.html", page="lecturers", title="Quản lý giảng viên")


@bp.get("/lecturers/<lid>")
@login_required
def lecturer_detail(lid):
    u = current_user()
    if u["role"] == "LECTURER" and u.get("lecturer_id") != lid:
        return render_template("403.html"), 403  # không xem hồ sơ người khác
    if not db.get("lecturers", lid):
        abort(404)
    return render_template("lecturer_detail.html", page="lecturers" if u["role"] in STAFF else "profile",
                           title="Hồ sơ giảng viên", lid=lid)


def _simple(rule, endpoint, template, page, title, roles):
    def view():
        return render_template(template, page=page, title=title)
    view.__name__ = endpoint
    bp.add_url_rule(rule, endpoint, roles_required(*roles)(view))


ALL = tuple(C.ROLES)
_simple("/faculties", "faculties", "faculties.html", "faculties", "Quản lý khoa", STAFF)
_simple("/departments", "departments", "departments.html", "departments", "Quản lý bộ môn", STAFF)
_simple("/contracts", "contracts", "contracts.html", "contracts", "Quản lý hợp đồng", STAFF)
_simple("/attendance", "attendance", "attendance.html", "attendance", "Chấm công", ALL)
_simple("/leave", "leave", "leave.html", "leave", "Nghỉ phép", ALL)
_simple("/evaluations", "evaluations", "evaluations.html", "evaluations", "Đánh giá giảng viên", ALL)
_simple("/notifications", "notifications", "notifications.html", "notifications", "Thông báo", ALL)
_simple("/audit-logs", "audit_logs", "audit_logs.html", "audit", "Nhật ký hệ thống", ("ADMIN",))
_simple("/settings", "settings", "settings.html", "settings", "Cài đặt", ALL)
