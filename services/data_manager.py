"""DataManager - NƠI DUY NHẤT đọc/ghi file JSON của hệ thống (không dùng SQL).

Mỗi "collection" là một file data/<name>.json chứa list các dict (hoặc 1 dict với system_settings).
Ghi file theo kiểu atomic (ghi file tạm rồi os.replace) và có khoá luồng để tránh hỏng dữ liệu.
Quan hệ giữa các bảng dùng ID tham chiếu (vd lecturer.faculty_id = "CNTT")."""
import json
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime

from config import Config

COLLECTIONS = ["users", "lecturers", "faculties", "departments", "contracts", "attendance",
               "leave_requests", "evaluations", "notifications", "audit_logs", "system_settings"]


class DataManager:
    def __init__(self, data_dir):
        self.dir = data_dir
        self._lock = threading.RLock()
        os.makedirs(self.dir, exist_ok=True)

    # ------------------------------------------------------------ đọc / ghi file
    def _path(self, name):
        if name not in COLLECTIONS:
            raise ValueError(f"Collection không hợp lệ: {name}")
        return os.path.join(self.dir, f"{name}.json")

    def exists(self, name):
        return os.path.exists(self._path(name))

    def read(self, name, default=None):
        with self._lock:
            try:
                with open(self._path(name), encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return [] if default is None else default

    def write(self, name, data):
        with self._lock:
            fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path(name))

    # ------------------------------------------------------------ CRUD
    def all(self, name):
        return self.read(name)

    def get(self, name, id_):
        return next((i for i in self.all(name) if i.get("id") == id_), None)

    def find(self, name, predicate=None, **eq):
        """Lọc theo điều kiện bằng (find('users', role='ADMIN')) và/hoặc hàm predicate."""
        out = []
        for i in self.all(name):
            if all(i.get(k) == v for k, v in eq.items()) and (predicate is None or predicate(i)):
                out.append(i)
        return out

    def find_one(self, name, predicate=None, **eq):
        r = self.find(name, predicate, **eq)
        return r[0] if r else None

    def count(self, name, **eq):
        return len(self.find(name, **eq))

    def next_id(self, name, prefix, width=3):
        """Sinh ID tự động dạng PREFIX + số tăng dần, vd HD021."""
        nums = [int(m.group(1)) for i in self.all(name)
                if (m := re.fullmatch(rf"{re.escape(prefix)}(\d+)", str(i.get("id", ""))))]
        return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"

    def insert(self, name, item, prefix=None, width=3):
        with self._lock:
            rows = self.all(name)
            if not item.get("id"):
                item["id"] = self.next_id(name, prefix or name[:2].upper(), width)
            if any(r.get("id") == item["id"] for r in rows):
                raise ValueError(f"ID {item['id']} đã tồn tại")
            rows.append(item)
            self.write(name, rows)
            return item

    def update(self, name, id_, changes):
        with self._lock:
            rows = self.all(name)
            for r in rows:
                if r.get("id") == id_:
                    r.update(changes)
                    self.write(name, rows)
                    return r
            return None

    def delete(self, name, id_):
        return self.delete_where(name, lambda r: r.get("id") == id_) > 0

    def delete_where(self, name, predicate):
        with self._lock:
            rows = self.all(name)
            keep = [r for r in rows if not predicate(r)]
            if len(keep) != len(rows):
                self.write(name, keep)
            return len(rows) - len(keep)

    # ------------------------------------------------------------ backup / restore
    def backup(self, backup_root, label=""):
        """Copy toàn bộ thư mục data/ vào backup/YYYY-MM-DD_HH-MM-SS[_label]/."""
        with self._lock:
            name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + (f"_{label}" if label else "")
            dest = os.path.join(backup_root, name)
            os.makedirs(dest, exist_ok=True)
            for fn in os.listdir(self.dir):
                if fn.endswith(".json"):
                    shutil.copy2(os.path.join(self.dir, fn), os.path.join(dest, fn))
            return name

    def restore(self, backup_root, name):
        src = os.path.join(backup_root, name)
        if not os.path.isdir(src):
            raise FileNotFoundError("Không tìm thấy bản sao lưu")
        with self._lock:
            for fn in os.listdir(src):
                if fn.endswith(".json") and fn[:-5] in COLLECTIONS:
                    shutil.copy2(os.path.join(src, fn), os.path.join(self.dir, fn))

    def list_backups(self, backup_root):
        out = []
        if os.path.isdir(backup_root):
            for n in sorted(os.listdir(backup_root), reverse=True):
                p = os.path.join(backup_root, n)
                if os.path.isdir(p):
                    files = [f for f in os.listdir(p) if f.endswith(".json")]
                    size = sum(os.path.getsize(os.path.join(p, f)) for f in files)
                    out.append({"name": n, "files": len(files), "size": size})
        return out


db = DataManager(Config.DATA_DIR)
