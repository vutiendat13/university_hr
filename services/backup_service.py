"""Sao lưu / khôi phục / export / import dữ liệu JSON."""
import json
import os
import re
import shutil

from config import Config
from services.data_manager import COLLECTIONS, db

NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(_[A-Za-z0-9\-]+)?$")  # chống path traversal


def create(label=""):
    return db.backup(Config.BACKUP_DIR, label)


def listing():
    return db.list_backups(Config.BACKUP_DIR)


def restore(name):
    if not NAME_RE.match(name or ""):
        raise ValueError("Tên bản sao lưu không hợp lệ")
    create("truoc-khi-restore")  # luôn sao lưu trạng thái hiện tại trước khi ghi đè
    db.restore(Config.BACKUP_DIR, name)


def remove(name):
    if not NAME_RE.match(name or ""):
        raise ValueError("Tên bản sao lưu không hợp lệ")
    path = os.path.join(Config.BACKUP_DIR, name)
    if not os.path.isdir(path):
        raise FileNotFoundError("Không tìm thấy bản sao lưu")
    shutil.rmtree(path)


def export_all():
    return {name: db.read(name, {} if name == "system_settings" else None) for name in COLLECTIONS}


def import_all(payload):
    """Import từ file export. Chỉ nhận đúng tên collection + kiểu dữ liệu; sao lưu trước khi ghi."""
    if not isinstance(payload, dict) or not payload:
        raise ValueError("File import không đúng định dạng")
    for name, data in payload.items():
        if name not in COLLECTIONS:
            raise ValueError(f"Collection không được hỗ trợ: {name}")
        if name == "system_settings":
            ok = isinstance(data, dict)
        else:
            ok = isinstance(data, list) and all(isinstance(r, dict) and "id" in r for r in data)
        if not ok:
            raise ValueError(f"Dữ liệu '{name}' không hợp lệ")
    if "users" in payload and not any(u.get("role") == "ADMIN" for u in payload["users"]):
        raise ValueError("Dữ liệu import phải có ít nhất một tài khoản ADMIN")
    create("truoc-khi-import")
    for name, data in payload.items():
        db.write(name, data)
    return list(payload)
