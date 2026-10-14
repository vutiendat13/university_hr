"""Xác thực: kiểm tra mật khẩu (Werkzeug hash), khoá tạm khi nhập sai nhiều lần, lấy user từ session."""
import time

from flask import g, session
from werkzeug.security import check_password_hash

from services.data_manager import db

MAX_FAILS, LOCK_SECONDS = 5, 300
_fails = {}  # "ip|username" -> [số lần sai, thời điểm hết khoá]


def authenticate(username, password, ip):
    """Trả về (user, lỗi). Mật khẩu luôn so sánh qua hash, không bao giờ lưu plain text."""
    key = f"{ip}|{username.lower()}"
    cnt, until = _fails.get(key, [0, 0])
    if until > time.time():
        return None, f"Tài khoản tạm khoá do nhập sai nhiều lần. Thử lại sau {int((until - time.time()) // 60) + 1} phút"
    user = db.find_one("users", username=username.lower())
    if user and user.get("active", True) and check_password_hash(user["password_hash"], password):
        _fails.pop(key, None)
        return user, None
    cnt += 1
    _fails[key] = [cnt, time.time() + LOCK_SECONDS if cnt >= MAX_FAILS else 0]
    if user and not user.get("active", True):
        return None, "Tài khoản đã bị vô hiệu hoá"
    return None, "Tên đăng nhập hoặc mật khẩu không đúng"


def current_user():
    """User hiện tại, đọc lại từ JSON mỗi request để đổi quyền/khoá tài khoản có hiệu lực ngay."""
    if "user" not in g:
        uid = session.get("uid")
        u = db.get("users", uid) if uid else None
        g.user = u if u and u.get("active", True) else None
    return g.user


def public_user(u):
    return {k: u.get(k) for k in ("id", "username", "full_name", "role", "email", "lecturer_id")} if u else None
