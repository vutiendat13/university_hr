"""Đăng nhập / đăng xuất / quên mật khẩu / đổi mật khẩu."""
import secrets

from flask import Blueprint, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from services import lecturer_service as ls
from services import notification_service as ns
from services.auth_service import authenticate, current_user, public_user
from services.data_manager import db
from utils.decorators import login_required
from utils.helpers import audit, today
from utils.validators import password_error

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_page():
    if current_user():
        return redirect("/dashboard")
    return render_template("login.html", settings=ls.get_settings())


@bp.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    username, password = str(d.get("username", "")).strip(), str(d.get("password", ""))
    if not username or not password:
        return jsonify(message="Vui lòng nhập tên đăng nhập và mật khẩu"), 422
    user, err = authenticate(username, password, request.remote_addr)
    if not user:
        audit("Đăng nhập thất bại", username, user={"username": username.lower(), "role": ""})
        return jsonify(message=err), 401
    session.clear()
    session.update(uid=user["id"], username=user["username"], role=user["role"], csrf=secrets.token_hex(16))
    session.permanent = bool(d.get("remember"))
    ns.check_contracts(int(ls.get_settings()["contract_warning_days"]))
    audit("Đăng nhập", "-", user=user)
    return jsonify(user=public_user(user), csrf=session["csrf"], redirect="/dashboard")


@bp.post("/api/auth/logout")
@login_required
def logout():
    audit("Đăng xuất", "-")
    session.clear()
    return jsonify(message="Đã đăng xuất")


@bp.get("/api/auth/me")
@login_required
def me():
    return jsonify(user=public_user(current_user()))


@bp.post("/api/auth/forgot")
def forgot():
    """Không tiết lộ tài khoản có tồn tại hay không; Admin nhận thông báo để đặt lại mật khẩu."""
    username = str((request.get_json(silent=True) or {}).get("username", "")).strip().lower()
    user = db.find_one("users", username=username) if username else None
    if user:
        ns.notify_roles(["ADMIN"], "system", f"Tài khoản '{username}' yêu cầu đặt lại mật khẩu", "/settings",
                        key=f"pwreset:{username}:{today()}")
        audit("Yêu cầu đặt lại mật khẩu", username, user={"username": username, "role": ""})
    return jsonify(message="Nếu tài khoản tồn tại, yêu cầu đã được gửi tới Quản trị viên để đặt lại mật khẩu.")


@bp.post("/api/auth/change-password")
@login_required
def change_password():
    d, user = request.get_json(silent=True) or {}, current_user()
    if not check_password_hash(user["password_hash"], str(d.get("current", ""))):
        return jsonify(message="Mật khẩu hiện tại không đúng", errors={"current": "Mật khẩu hiện tại không đúng"}), 422
    err = password_error(str(d.get("new", "")))
    if err:
        return jsonify(message=err, errors={"new": err}), 422
    db.update("users", user["id"], {"password_hash": generate_password_hash(d["new"])})
    audit("Đổi mật khẩu", user["username"])
    return jsonify(message="Đã đổi mật khẩu")
