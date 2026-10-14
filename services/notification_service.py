"""Tạo / truy vấn thông báo. Mỗi thông báo gắn với 1 user cụ thể (fan-out theo role khi cần)."""
from datetime import timedelta

from services.data_manager import db
from utils.helpers import now_str, today
from utils.validators import parse_date


def notify(user_ids, type_, message, link="", key=None):
    """type_: contract | leave | evaluation | system. `key` dùng để không tạo thông báo trùng."""
    rows, changed = db.all("notifications"), False
    existing = {(n["user_id"], n.get("key")) for n in rows if n.get("key")}
    seq = max([int(n["id"][2:]) for n in rows if n["id"][2:].isdigit()] or [0])
    for uid in set(user_ids):
        if key and (uid, key) in existing:
            continue
        seq += 1
        rows.append({"id": f"TB{seq:05d}", "user_id": uid,
                     "type": type_, "message": message, "link": link, "read": False,
                     "created_at": now_str(), "key": key})
        changed = True
    if changed:
        db.write("notifications", rows[-2000:])


def notify_roles(roles, type_, message, link="", key=None):
    notify([u["id"] for u in db.all("users") if u["role"] in roles and u.get("active", True)], type_, message, link, key)


def notify_lecturer(lecturer_id, type_, message, link="", key=None):
    notify([u["id"] for u in db.find("users", lecturer_id=lecturer_id)], type_, message, link, key)


def check_contracts(warn_days):
    """Hợp đồng sắp hết hạn -> thông báo Admin/Manager (mỗi hợp đồng chỉ báo 1 lần)."""
    limit = today() + timedelta(days=warn_days)
    for c in db.all("contracts"):
        e = parse_date(c.get("end_date"))
        if e and today() <= e <= limit:
            notify_roles(["ADMIN", "MANAGER"], "contract",
                         f"Hợp đồng {c['lecturer_id']} ({c['id']}) sắp hết hạn vào {e.strftime('%d/%m/%Y')}",
                         "/contracts", key=f"exp:{c['id']}:{c['end_date']}")


def for_user(user_id):
    rows = [n for n in db.all("notifications") if n["user_id"] == user_id]
    return sorted(rows, key=lambda n: n["created_at"], reverse=True)
