"""Cấu hình tập trung và các hằng số nghiệp vụ dùng chung cho backend + frontend."""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _secret_key():
    """SECRET_KEY lấy từ biến môi trường HR_SECRET_KEY; nếu chưa có thì sinh ngẫu nhiên
    và lưu vào instance/secret.key (không nằm trong source code, không commit lên Git)."""
    env = os.environ.get("HR_SECRET_KEY")
    if env:
        return env
    path = os.path.join(BASE_DIR, "instance", "secret.key")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


class Config:
    SECRET_KEY = _secret_key()
    DATA_DIR = os.environ.get("HR_DATA_DIR", os.path.join(BASE_DIR, "data"))
    BACKUP_DIR = os.environ.get("HR_BACKUP_DIR", os.path.join(BASE_DIR, "backup"))
    UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("HR_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB cho upload / import


# ---------------------------------------------------------------- Hằng số nghiệp vụ
ROLES = ["ADMIN", "MANAGER", "LECTURER"]
GENDERS = ["Nam", "Nữ"]
DEGREES = ["Cử nhân", "Thạc sĩ", "Tiến sĩ", "PGS", "GS"]
POSITIONS = ["Trợ giảng", "Giảng viên", "Giảng viên chính", "Phó trưởng bộ môn",
             "Trưởng bộ môn", "Phó trưởng khoa", "Trưởng khoa"]
LECTURER_CONTRACT_TYPES = ["Chính thức", "Hợp đồng", "Thỉnh giảng"]
WORK_STATUS = ["Đang làm việc", "Đã nghỉ việc"]
FACULTY_STATUS = ["Hoạt động", "Tạm ngưng"]
CONTRACT_KINDS = ["Biên chế", "Hợp đồng 1 năm", "Hợp đồng 3 năm", "Thỉnh giảng"]
LEAVE_TYPES = ["Nghỉ phép năm", "Nghỉ ốm", "Nghỉ việc riêng", "Nghỉ thai sản", "Nghỉ không lương"]
LEAVE_STATUS = ["Chờ duyệt", "Đã duyệt", "Từ chối"]
ATTENDANCE_STATUS = ["Có mặt", "Đi muộn", "Vắng", "Nghỉ phép"]
CRITERIA = {"expertise": "Chuyên môn", "teaching": "Giảng dạy", "attitude": "Thái độ",
            "research": "Nghiên cứu", "contribution": "Đóng góp", "discipline": "Kỷ luật"}
GRADES = [(4.5, "Xuất sắc"), (3.5, "Tốt"), (2.5, "Khá"), (2.0, "Trung bình"), (0, "Chưa đạt")]

DEFAULT_SETTINGS = {
    "system_name": "Hệ thống quản lý nhân sự giảng viên",
    "school_name": "Trường Đại học Hải Phòng",
    "version": "1.0.0",
    "contract_warning_days": 60,   # cảnh báo hợp đồng sắp hết hạn trước N ngày
    "work_start": "07:30",         # quá giờ này tính là "Đi muộn"
    "work_end": "17:00",
}

# Menu sidebar: nguồn duy nhất cho điều hướng + quyền xem trang
NAV = [
    {"key": "dashboard", "path": "/dashboard", "label": "Tổng quan", "icon": "fa-gauge-high", "roles": ROLES},
    {"key": "profile", "path": "/me", "label": "Hồ sơ của tôi", "icon": "fa-id-card", "roles": ["LECTURER"]},
    {"key": "lecturers", "path": "/lecturers", "label": "Giảng viên", "icon": "fa-user-tie", "roles": ["ADMIN", "MANAGER"]},
    {"key": "faculties", "path": "/faculties", "label": "Khoa", "icon": "fa-building-columns", "roles": ["ADMIN", "MANAGER"]},
    {"key": "departments", "path": "/departments", "label": "Bộ môn", "icon": "fa-sitemap", "roles": ["ADMIN", "MANAGER"]},
    {"key": "contracts", "path": "/contracts", "label": "Hợp đồng", "icon": "fa-file-signature", "roles": ["ADMIN", "MANAGER"]},
    {"key": "attendance", "path": "/attendance", "label": "Chấm công", "icon": "fa-calendar-check", "roles": ROLES},
    {"key": "leave", "path": "/leave", "label": "Nghỉ phép", "icon": "fa-umbrella-beach", "roles": ROLES},
    {"key": "evaluations", "path": "/evaluations", "label": "Đánh giá", "icon": "fa-star-half-stroke", "roles": ROLES},
    {"key": "notifications", "path": "/notifications", "label": "Thông báo", "icon": "fa-bell", "roles": ROLES},
    {"key": "audit", "path": "/audit-logs", "label": "Nhật ký hệ thống", "icon": "fa-clock-rotate-left", "roles": ["ADMIN"]},
    {"key": "settings", "path": "/settings", "label": "Cài đặt", "icon": "fa-gear", "roles": ROLES},
]
