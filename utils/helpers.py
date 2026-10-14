"""Hàm tiện ích dùng chung: thời gian, nhật ký thao tác (audit log), phân trang."""
import unicodedata
from datetime import date, datetime

from flask import request, session

from services.data_manager import db

MAX_AUDIT = 5000


def today():
    return date.today()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fold(text):
    """Bỏ dấu tiếng Việt + chữ thường để tìm kiếm 'nguyen' khớp 'Nguyễn'."""
    s = unicodedata.normalize("NFD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def audit(action, target="", user=None):
    """Ghi nhật ký thao tác: user, action, target, timestamp, ip."""
    uid = user.get("username") if user else session.get("username", "anonymous")
    try:
        ip = request.remote_addr
    except RuntimeError:
        ip = "-"
    logs = db.all("audit_logs")
    entry = {"id": db.next_id("audit_logs", "LOG", 5), "user": uid,
             "role": user.get("role") if user else session.get("role", ""),
             "action": action, "target": target, "timestamp": now_str(), "ip": ip}
    logs.append(entry)
    db.write("audit_logs", logs[-MAX_AUDIT:])
    return entry


def paginate(items, page, per_page):
    total = len(items)
    per_page = max(1, min(per_page, 500))
    pages = max(1, -(-total // per_page))
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    return {"items": items[start:start + per_page], "total": total, "page": page, "pages": pages}
