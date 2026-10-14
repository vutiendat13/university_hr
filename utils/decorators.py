"""Decorator xác thực + phân quyền. Luôn kiểm tra ở backend, không tin frontend."""
from functools import wraps

from flask import jsonify, redirect, render_template, request, url_for

from services.auth_service import current_user


def _is_api():
    return request.path.startswith("/api/")


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user():
            if _is_api():
                return jsonify(message="Phiên đăng nhập đã hết hạn"), 401
            return redirect(url_for("auth.login_page"))
        return fn(*a, **kw)
    return wrapper


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if current_user()["role"] not in roles:
                if _is_api():
                    return jsonify(message="Bạn không có quyền thực hiện chức năng này"), 403
                return render_template("403.html"), 403
            return fn(*a, **kw)
        return wrapper
    return deco
