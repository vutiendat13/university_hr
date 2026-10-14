"""Validate dữ liệu đầu vào theo schema khai báo cho từng resource.

SCHEMAS[resource] = [(tên_field, kiểu, bắt_buộc, tham_số)]. Hàm validate() trả về (clean, errors);
cross_check() kiểm tra các ràng buộc liên bảng (trùng mã, khoá ngoại, trùng lịch...)."""
import re
from datetime import date, datetime

import config as C

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^(0|\+84)(3|5|7|8|9)\d{8}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def password_error(pw):
    if len(pw or "") < 8 or not re.search(r"[A-Z]", pw) or not re.search(r"[a-z]", pw) or not re.search(r"\d", pw):
        return "Mật khẩu tối thiểu 8 ký tự, gồm chữ hoa, chữ thường và số"
    return None


SCHEMAS = {
    "lecturers": [
        ("id", "code", True, r"[A-Z0-9]{3,12}"), ("full_name", "str", True, (2, 80)),
        ("dob", "date", True, None), ("gender", "choice", True, C.GENDERS),
        ("cccd", "regex", True, (r"\d{12}", "CCCD gồm đúng 12 chữ số")), ("email", "email", True, None),
        ("phone", "phone", True, None), ("address", "str", False, (0, 200)),
        ("faculty_id", "fk", True, "faculties"), ("department_id", "fk", True, "departments"),
        ("position", "choice", True, C.POSITIONS), ("degree", "choice", True, C.DEGREES),
        ("join_date", "date", True, None), ("contract_type", "choice", True, C.LECTURER_CONTRACT_TYPES),
        ("work_status", "choice", False, C.WORK_STATUS), ("avatar", "str", False, (0, 200)),
    ],
    "faculties": [
        ("id", "code", True, r"[A-Z0-9]{2,10}"), ("name", "str", True, (3, 100)),
        ("dean", "str", False, (0, 80)), ("description", "str", False, (0, 300)),
        ("status", "choice", True, C.FACULTY_STATUS),
    ],
    "departments": [
        ("id", "code", False, r"[A-Z0-9]{2,12}"), ("name", "str", True, (3, 100)),
        ("faculty_id", "fk", True, "faculties"), ("head", "str", False, (0, 80)),
    ],
    "contracts": [
        ("lecturer_id", "fk", True, "lecturers"), ("type", "choice", True, C.CONTRACT_KINDS),
        ("start_date", "date", True, None), ("end_date", "date", False, None), ("note", "str", False, (0, 300)),
    ],
    "attendance": [
        ("lecturer_id", "fk", True, "lecturers"), ("date", "date", True, None),
        ("check_in", "time", False, None), ("check_out", "time", False, None),
        ("status", "choice", True, C.ATTENDANCE_STATUS), ("note", "str", False, (0, 200)),
    ],
    "leave": [
        ("lecturer_id", "fk", True, "lecturers"), ("type", "choice", True, C.LEAVE_TYPES),
        ("from_date", "date", True, None), ("to_date", "date", True, None), ("reason", "str", True, (5, 500)),
    ],
    "evaluations": [("lecturer_id", "fk", True, "lecturers"), ("period", "str", True, (3, 40)),
                    ("comment", "str", False, (0, 500))]
    + [(k, "int", True, (1, 5)) for k in C.CRITERIA],
    "users": [
        ("username", "regex", True, (r"[a-z0-9_.]{3,30}", "Tên đăng nhập 3-30 ký tự: chữ thường, số, _ hoặc .")),
        ("full_name", "str", True, (2, 80)), ("role", "choice", True, C.ROLES),
        ("email", "email", False, None), ("lecturer_id", "fk", False, "lecturers"), ("active", "bool", False, None),
    ],
}
FK_FILE = {"leave": "leave_requests"}


def _check(kind, val, arg, db):
    if kind == "str":
        s = str(val).strip()
        return (s, None) if arg[0] <= len(s) <= arg[1] else (None, f"Độ dài phải từ {arg[0]} đến {arg[1]} ký tự")
    if kind == "code":
        s = str(val).strip().upper()
        return (s, None) if re.fullmatch(arg, s) else (None, "Mã chỉ gồm chữ/số, không dấu, không khoảng trắng")
    if kind == "regex":
        s = str(val).strip()
        return (s, None) if re.fullmatch(arg[0], s) else (None, arg[1])
    if kind == "email":
        s = str(val).strip().lower()
        return (s, None) if EMAIL_RE.match(s) else (None, "Email không đúng định dạng")
    if kind == "phone":
        s = re.sub(r"[\s.\-]", "", str(val))
        return (s, None) if PHONE_RE.match(s) else (None, "Số điện thoại không đúng định dạng (VD: 0912345678)")
    if kind == "date":
        d = parse_date(val)
        return (d.isoformat(), None) if d else (None, "Ngày không hợp lệ (YYYY-MM-DD)")
    if kind == "time":
        return (val, None) if TIME_RE.match(str(val)) else (None, "Giờ không hợp lệ (HH:MM)")
    if kind == "choice":
        return (val, None) if val in arg else (None, "Giá trị không hợp lệ")
    if kind == "int":
        try:
            n = int(val)
        except (TypeError, ValueError):
            return None, "Phải là số nguyên"
        return (n, None) if arg[0] <= n <= arg[1] else (None, f"Giá trị từ {arg[0]} đến {arg[1]}")
    if kind == "fk":
        return (val, None) if db.get(arg, val) else (None, "Dữ liệu tham chiếu không tồn tại")
    if kind == "bool":
        return bool(val), None
    return val, None


def validate(resource, data, db, partial=False, only=None):
    """partial=True: chỉ kiểm tra field có trong data (dùng cho PUT). only: giới hạn danh sách field."""
    clean, errors = {}, {}
    for name, kind, required, arg in SCHEMAS[resource]:
        if only is not None and name not in only:
            continue
        if partial and name not in data:
            continue
        val = data.get(name)
        if isinstance(val, str):
            val = val.strip()
        if val in (None, ""):
            if required:
                errors[name] = "Trường này là bắt buộc"
            elif kind != "bool":
                clean[name] = ""
            continue
        fk_db_arg = FK_FILE.get(arg, arg) if kind == "fk" else arg
        v, err = _check(kind, val, fk_db_arg, db)
        if err:
            errors[name] = err
        else:
            clean[name] = v
    return clean, errors


def cross_check(resource, clean, existing, db, errors):
    """Ràng buộc liên field / liên bảng. `clean` đã gộp với bản ghi cũ khi cập nhật."""
    eid = existing["id"] if existing else None
    if resource == "lecturers":
        if not existing and "id" not in errors and db.get("lecturers", clean.get("id")):
            errors["id"] = "Mã giảng viên đã tồn tại"
        e = clean.get("email")
        if e and "email" not in errors and db.find_one("lecturers", lambda l: l["email"] == e and l["id"] != eid):
            errors["email"] = "Email đã được sử dụng"
        dep = db.get("departments", clean.get("department_id")) if "department_id" not in errors else None
        if dep and clean.get("faculty_id") and dep["faculty_id"] != clean["faculty_id"]:
            errors["department_id"] = "Bộ môn không thuộc khoa đã chọn"
        dob, jd = parse_date(clean.get("dob")), parse_date(clean.get("join_date"))
        if dob and "dob" not in errors and not 21 <= (date.today() - dob).days / 365.25 <= 75:
            errors["dob"] = "Tuổi phải từ 21 đến 75"
        if dob and jd and "join_date" not in errors and (jd - dob).days / 365.25 < 18:
            errors["join_date"] = "Ngày vào trường không hợp lệ so với ngày sinh"
    elif resource == "faculties":
        if not existing and "id" not in errors and db.get("faculties", clean.get("id")):
            errors["id"] = "Mã khoa đã tồn tại"
    elif resource == "departments":
        n, f = clean.get("name", "").lower(), clean.get("faculty_id")
        if n and f and db.find_one("departments", lambda d: d["name"].lower() == n and d["faculty_id"] == f and d["id"] != eid):
            errors["name"] = "Bộ môn đã tồn tại trong khoa này"
        if not existing and clean.get("id") and db.get("departments", clean["id"]):
            errors["id"] = "Mã bộ môn đã tồn tại"
    elif resource == "contracts":
        s, e = parse_date(clean.get("start_date")), parse_date(clean.get("end_date"))
        if clean.get("type") != "Biên chế" and not clean.get("end_date"):
            errors["end_date"] = "Hợp đồng có thời hạn phải có ngày kết thúc"
        elif s and e and e < s:
            errors["end_date"] = "Ngày kết thúc phải sau ngày bắt đầu"
    elif resource == "attendance":
        ci, co = clean.get("check_in"), clean.get("check_out")
        if ci and co and co < ci:
            errors["check_out"] = "Giờ ra phải sau giờ vào"
        if clean.get("lecturer_id") and clean.get("date") and "date" not in errors and db.find_one(
                "attendance", lambda a: a["lecturer_id"] == clean["lecturer_id"] and a["date"] == clean["date"] and a["id"] != eid):
            errors["date"] = "Giảng viên đã có bản ghi chấm công ngày này"
    elif resource == "leave":
        f, t = parse_date(clean.get("from_date")), parse_date(clean.get("to_date"))
        if f and t:
            if t < f:
                errors["to_date"] = "Ngày kết thúc phải sau ngày bắt đầu"
            elif (t - f).days > 180:
                errors["to_date"] = "Thời gian nghỉ tối đa 180 ngày"
            elif db.find_one("leave_requests", lambda r: r["lecturer_id"] == clean["lecturer_id"] and r["status"] != "Từ chối"
                             and r["from_date"] <= clean["to_date"] and clean["from_date"] <= r["to_date"]):
                errors["from_date"] = "Trùng với một đơn nghỉ phép khác đang chờ duyệt/đã duyệt"
    elif resource == "evaluations":
        if not existing and clean.get("lecturer_id") and clean.get("period") and db.find_one(
                "evaluations", lambda x: x["lecturer_id"] == clean["lecturer_id"] and x["period"] == clean["period"]):
            errors["period"] = "Giảng viên đã được đánh giá trong kỳ này"
    elif resource == "users":
        u = clean.get("username")
        if u and "username" not in errors and db.find_one("users", lambda x: x["username"] == u and x["id"] != eid):
            errors["username"] = "Tên đăng nhập đã tồn tại"
        lid = clean.get("lecturer_id")
        if lid and "lecturer_id" not in errors and db.find_one("users", lambda x: x.get("lecturer_id") == lid and x["id"] != eid):
            errors["lecturer_id"] = "Giảng viên này đã có tài khoản"
    return errors
