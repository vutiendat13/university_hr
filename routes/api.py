"""REST API. Mọi endpoint đều kiểm tra đăng nhập + quyền theo role ở BACKEND.

Các resource CRUD (lecturers, faculties, departments, contracts, attendance, leave, evaluations, users,
audit-logs) dùng chung một bộ handler, khai báo quyền trong bảng RES. Các nghiệp vụ đặc thù
(duyệt nghỉ phép, chấm công, backup...) là endpoint riêng bên dưới."""
import csv
import io
import json
import os
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, Response, jsonify, request
from werkzeug.security import generate_password_hash

import config as C
from config import Config
from services import backup_service
from services import lecturer_service as ls
from services import notification_service as ns
from services.auth_service import current_user
from services.data_manager import COLLECTIONS, db
from utils.decorators import login_required, roles_required
from utils.helpers import audit, fold, now_str, paginate, today
from utils.validators import TIME_RE, cross_check, parse_date, password_error, validate

bp = Blueprint("api", __name__, url_prefix="/api")
ALL, STAFF, ADM = tuple(C.ROLES), ("ADMIN", "MANAGER"), ("ADMIN",)
SELF_FIELDS = ("phone", "address", "email", "avatar")  # giảng viên chỉ được tự sửa các trường này

# Bảng quyền + cấu hình từng resource
RES = {
    "lecturers": dict(file="lecturers", label="giảng viên", read=ALL, create=STAFF, update=ALL, delete=ADM, own="id",
                      search=("id", "full_name", "email", "phone", "degree", "position", "faculty_id", "faculty_name", "department_name"),
                      filters=("faculty_id", "department_id", "gender", "degree", "position", "status", "contract_type"), sort="id"),
    "faculties": dict(file="faculties", label="khoa", read=ALL, create=ADM, update=ADM, delete=ADM,
                      search=("id", "name", "dean"), filters=("status",), sort="id"),
    "departments": dict(file="departments", label="bộ môn", read=ALL, create=STAFF, update=STAFF, delete=STAFF,
                        search=("id", "name", "head", "faculty_name"), filters=("faculty_id",), sort="faculty_id", prefix="BM"),
    "contracts": dict(file="contracts", label="hợp đồng", read=ALL, create=ADM, update=ADM, delete=ADM, own="lecturer_id",
                      search=("id", "lecturer_id", "lecturer_name", "type", "faculty_id"),
                      filters=("faculty_id", "lecturer_id", "type", "status"), sort="id", prefix="HD"),
    "attendance": dict(file="attendance", label="chấm công", read=ALL, create=ADM, update=ADM, delete=ADM, own="lecturer_id",
                       search=("lecturer_id", "lecturer_name", "note"), filters=("faculty_id", "lecturer_id", "status"),
                       sort="date", order="desc", prefix="CC", width=5),
    "leave": dict(file="leave_requests", label="đơn nghỉ phép", read=ALL, create=ALL, update=(), delete=ADM, own="lecturer_id",
                  search=("id", "lecturer_id", "lecturer_name", "type", "reason"),
                  filters=("faculty_id", "lecturer_id", "type", "status"), sort="created_at", order="desc", prefix="NP"),
    "evaluations": dict(file="evaluations", label="đánh giá", read=ALL, create=STAFF, update=STAFF, delete=ADM, own="lecturer_id",
                        search=("id", "lecturer_id", "lecturer_name", "period", "grade"),
                        filters=("faculty_id", "lecturer_id", "period", "grade"), sort="created_at", order="desc", prefix="DG"),
    "users": dict(file="users", label="tài khoản", read=ADM, create=ADM, update=ADM, delete=ADM,
                  search=("username", "full_name", "email", "role"), filters=("role",), sort="id", prefix="U"),
    "audit-logs": dict(file="audit_logs", label="nhật ký", read=ADM, create=(), update=(), delete=(),
                       search=("user", "action", "target", "ip"), filters=("user", "role"), sort="timestamp", order="desc"),
}
SCHEMA_OF = {"audit-logs": None}


def err(msg, code=400, errors=None):
    return jsonify(message=msg, errors=errors or {}), code


def forbidden():
    return err("Bạn không có quyền thực hiện chức năng này", 403)


def scope(name, rows, user):
    """Giảng viên chỉ thấy dữ liệu của chính mình (lọc ở backend)."""
    own = RES[name].get("own")
    if user["role"] == "LECTURER" and own:
        return [r for r in rows if r.get(own) and r.get(own) == user.get("lecturer_id")]
    return rows


def target_of(name, rec):
    lid = rec.get("lecturer_id")
    return f"{rec['id']} ({lid})" if lid and name != "users" else str(rec.get("id", ""))


def sort_key(k):
    return lambda r: fold(r.get(k)) if isinstance(r.get(k), str) else (r.get(k) or 0)


# ------------------------------------------------------------------ CRUD tổng quát
@login_required
def list_view(name):
    cfg, user, a = RES[name], current_user(), request.args
    if user["role"] not in cfg["read"]:
        return forbidden()
    ctx = ls.Lookup()
    rows = [ls.enrich(name, r, ctx) for r in scope(name, db.all(cfg["file"]), user)]
    for f in cfg.get("filters", ()):
        if a.get(f):
            rows = [r for r in rows if str(r.get(f, "")) == a[f]]
    if a.get("date"):
        rows = [r for r in rows if r.get("date") == a["date"]]
    if a.get("month"):
        rows = [r for r in rows if str(r.get("date") or r.get("from_date") or "").startswith(a["month"])]
    if a.get("date_from"):
        rows = [r for r in rows if str(r.get("date", "")) >= a["date_from"]]
    if a.get("date_to"):
        rows = [r for r in rows if str(r.get("date", "")) <= a["date_to"]]
    q = fold(a.get("q", "")).strip()
    if q:
        rows = [r for r in rows if any(q in fold(r.get(k, "")) for k in cfg["search"])]
    key = a.get("sort") if rows and a.get("sort") in rows[0] else cfg["sort"]
    desc = (a.get("order") or (cfg.get("order", "asc") if key == cfg["sort"] else "asc")) == "desc"
    sk = sort_key(key)
    rows.sort(key=lambda r: (sk(r), str(r.get("id", ""))), reverse=desc)  # id làm tiêu chí phụ để ổn định thứ tự
    return jsonify(paginate(rows, a.get("page", 1, type=int), a.get("per_page", 10, type=int)))


@login_required
def get_view(name, id_):
    cfg, user = RES[name], current_user()
    if user["role"] not in cfg["read"]:
        return forbidden()
    rows = scope(name, [r for r in db.all(cfg["file"]) if r["id"] == id_], user)
    return jsonify(ls.enrich(name, rows[0], ls.Lookup())) if rows else err("Không tìm thấy dữ liệu", 404)


def _build(name, c, data, user):
    """Bổ sung các trường do hệ thống sinh (trạng thái, điểm TB, hash mật khẩu...) cho bản ghi mới."""
    if name == "lecturers":
        c.setdefault("work_status", "Đang làm việc")
        c["work_status"] = c["work_status"] or "Đang làm việc"
    elif name == "leave":
        c.update(status="Chờ duyệt", history=[], created_at=now_str())
    elif name == "evaluations":
        _score(c); c.update(evaluator=user["full_name"], created_at=now_str())
    elif name == "users":
        c.update(password_hash=generate_password_hash(data["password"]), active=c.get("active", True))
    return c


def _score(c):
    c["avg"] = round(sum(c[k] for k in C.CRITERIA) / len(C.CRITERIA), 2)
    c["grade"] = ls.grade_of(c["avg"])


def _after_create(name, rec, user):
    if name == "leave":
        ns.notify_roles(STAFF, "leave", f"Có đơn nghỉ phép mới từ {rec['lecturer_id']}", "/leave")
    elif name == "evaluations":
        ns.notify_lecturer(rec["lecturer_id"], "evaluation", f"Bạn có đánh giá mới: {rec['period']}", "/evaluations")
    elif name == "contracts":
        ns.check_contracts(int(ls.get_settings()["contract_warning_days"]))


@login_required
def create_view(name):
    cfg, user = RES[name], current_user()
    if user["role"] not in cfg["create"]:
        return forbidden()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Dữ liệu gửi lên không hợp lệ")
    if name == "leave" and user["role"] == "LECTURER":  # giảng viên chỉ gửi đơn cho chính mình
        if not user.get("lecturer_id"):
            return err("Tài khoản chưa gắn với hồ sơ giảng viên", 400)
        data["lecturer_id"] = user["lecturer_id"]
    clean, errors = validate(name, data, db)
    cross_check(name, clean, None, db, errors)
    if name == "users":
        pe = password_error(data.get("password", ""))
        if pe:
            errors["password"] = pe
    if errors:
        return err("Dữ liệu không hợp lệ", 422, errors)
    rec = _build(name, clean, data, user)
    if name == "departments" and not rec.get("id"):
        rec.pop("id", None)
    try:
        rec = db.insert(cfg["file"], rec, cfg.get("prefix"), cfg.get("width", 3))
    except ValueError as e:
        return err(str(e), 422)
    _after_create(name, rec, user)
    audit(f"Thêm {cfg['label']}", target_of(name, rec))
    return jsonify(ls.enrich(name, rec, ls.Lookup())), 201


@login_required
def update_view(name, id_):
    cfg, user = RES[name], current_user()
    if user["role"] not in cfg["update"]:
        return forbidden()
    row = db.get(cfg["file"], id_)
    if not row or not scope(name, [row], user):
        return err("Không tìm thấy dữ liệu", 404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Dữ liệu gửi lên không hợp lệ")
    if name == "lecturers" and user["role"] == "LECTURER":
        data = {k: v for k, v in data.items() if k in SELF_FIELDS}
        if not data:
            return err("Bạn chỉ được cập nhật email, số điện thoại, địa chỉ và ảnh đại diện", 403)
    data.pop("id", None)
    if name == "users":
        data.pop("username", None) if row["username"] == "admin" else None
    clean, errors = validate(name, data, db, partial=True)
    merged = {**row, **clean}
    cross_check(name, merged, row, db, errors)
    if name == "users":
        if data.get("password"):
            pe = password_error(data["password"])
            if pe:
                errors["password"] = pe
            else:
                clean["password_hash"] = generate_password_hash(data["password"])
        admins = [u for u in db.all("users") if u["role"] == "ADMIN" and u.get("active", True) and u["id"] != id_]
        if (merged["role"] != "ADMIN" or not merged.get("active", True)) and row["role"] == "ADMIN" and not admins:
            errors["role"] = "Phải còn ít nhất một Admin đang hoạt động"
        if id_ == user["id"] and (merged["role"] != row["role"] or not merged.get("active", True)):
            errors["role"] = "Không thể đổi quyền hoặc khoá chính tài khoản đang đăng nhập"
    if errors:
        return err("Dữ liệu không hợp lệ", 422, errors)
    if name == "evaluations":
        _score(merged); clean.update(avg=merged["avg"], grade=merged["grade"])
    rec = db.update(cfg["file"], id_, clean)
    audit(f"Sửa {cfg['label']}", target_of(name, rec))
    return jsonify(ls.enrich(name, rec, ls.Lookup()))


@login_required
def delete_view(name, id_):
    cfg, user = RES[name], current_user()
    if user["role"] not in cfg["delete"]:
        return forbidden()
    row = db.get(cfg["file"], id_)
    if not row:
        return err("Không tìm thấy dữ liệu", 404)
    if name == "faculties" and (db.find("departments", faculty_id=id_) or db.find("lecturers", faculty_id=id_)):
        return err("Khoa còn bộ môn hoặc giảng viên, không thể xoá", 409)
    if name == "departments" and db.find("lecturers", department_id=id_):
        return err("Bộ môn còn giảng viên, hãy chuyển giảng viên sang bộ môn khác trước", 409)
    if name == "users":
        if id_ == user["id"]:
            return err("Không thể xoá tài khoản đang đăng nhập", 409)
        if row["role"] == "ADMIN" and not [u for u in db.all("users") if u["role"] == "ADMIN" and u["id"] != id_]:
            return err("Không thể xoá Admin cuối cùng", 409)
    if name == "lecturers":  # xoá dây chuyền dữ liệu liên quan
        for coll in ("contracts", "attendance", "leave_requests", "evaluations"):
            db.delete_where(coll, lambda r: r["lecturer_id"] == id_)
        uids = {u["id"] for u in db.find("users", lecturer_id=id_)}
        db.delete_where("users", lambda u: u["id"] in uids)
        db.delete_where("notifications", lambda n: n["user_id"] in uids)
    db.delete(cfg["file"], id_)
    audit(f"Xoá {cfg['label']}", target_of(name, row))
    return jsonify(message="Đã xoá")


for _n, _c in RES.items():
    bp.add_url_rule(f"/{_n}", f"list_{_n}", lambda n=_n: list_view(n), methods=["GET"])
    bp.add_url_rule(f"/{_n}/<id_>", f"get_{_n}", lambda id_, n=_n: get_view(n, id_), methods=["GET"])
    if _c["create"]:
        bp.add_url_rule(f"/{_n}", f"create_{_n}", lambda n=_n: create_view(n), methods=["POST"])
    if _c["update"]:
        bp.add_url_rule(f"/{_n}/<id_>", f"update_{_n}", lambda id_, n=_n: update_view(n, id_), methods=["PUT"])
    if _c["delete"]:
        bp.add_url_rule(f"/{_n}/<id_>", f"delete_{_n}", lambda id_, n=_n: delete_view(n, id_), methods=["DELETE"])


# ------------------------------------------------------------------ Meta, dashboard, hồ sơ
@bp.get("/meta")
@login_required
def meta():
    return jsonify(genders=C.GENDERS, degrees=C.DEGREES, positions=C.POSITIONS, lecturer_contract_types=C.LECTURER_CONTRACT_TYPES,
                   work_status=C.WORK_STATUS, faculty_status=C.FACULTY_STATUS, contract_kinds=C.CONTRACT_KINDS,
                   leave_types=C.LEAVE_TYPES, leave_status=C.LEAVE_STATUS, attendance_status=C.ATTENDANCE_STATUS,
                   criteria=C.CRITERIA, roles=C.ROLES, grades=[g for _, g in C.GRADES])


@bp.get("/dashboard/stats")
@roles_required(*STAFF)
def dashboard_stats():
    return jsonify(ls.dashboard_stats())


@bp.get("/dashboard/campus")
@login_required
def dashboard_campus():
    return jsonify(ls.campus_data())


@bp.get("/dashboard/me")
@login_required
def dashboard_me():
    lid = current_user().get("lecturer_id")
    return jsonify(ls.my_summary(lid) if lid else {})


@bp.get("/lecturers/<lid>/profile")
@login_required
def lecturer_profile(lid):
    user = current_user()
    if user["role"] == "LECTURER" and user.get("lecturer_id") != lid:
        return forbidden()
    p = ls.profile(lid, user["role"] == "ADMIN")
    return jsonify(p) if p else err("Không tìm thấy giảng viên", 404)


@bp.get("/lecturers/export.csv")
@roles_required(*STAFF)
def export_lecturers_csv():
    ctx = ls.Lookup()
    rows = [ls.enrich("lecturers", l, ctx) for l in db.all("lecturers")]
    cols = [("id", "Mã GV"), ("full_name", "Họ tên"), ("gender", "Giới tính"), ("dob", "Ngày sinh"), ("faculty_name", "Khoa"),
            ("department_name", "Bộ môn"), ("position", "Chức vụ"), ("degree", "Trình độ"), ("email", "Email"),
            ("phone", "Số điện thoại"), ("contract_type", "Loại hợp đồng"), ("status", "Trạng thái")]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([h for _, h in cols])
    for r in rows:
        w.writerow([("'" + str(r[k]) if k == "phone" else r.get(k, "")) for k, _ in cols])
    audit("Export CSV giảng viên", "lecturers")
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=giang-vien-{today()}.csv"})


# ------------------------------------------------------------------ Nghỉ phép: duyệt / từ chối
def _mark_leave_attendance(r):
    """Đơn được duyệt -> đánh dấu 'Nghỉ phép' vào chấm công cho các ngày làm việc đã qua trong khoảng nghỉ."""
    rows = db.all("attendance")
    have = {(a["lecturer_id"], a["date"]) for a in rows}
    d, end, n = parse_date(r["from_date"]), min(parse_date(r["to_date"]), today()), 0
    while d <= end:
        if d.weekday() < 5 and (r["lecturer_id"], d.isoformat()) not in have:
            n += 1
            rows.append({"id": f"CC{max([int(a['id'][2:]) for a in rows] or [0]) + 1:05d}", "lecturer_id": r["lecturer_id"],
                         "date": d.isoformat(), "check_in": "", "check_out": "", "status": "Nghỉ phép", "note": f"Đơn {r['id']}"})
        d += timedelta(days=1)
    if n:
        db.write("attendance", rows)


@bp.post("/leave/<id_>/<action>")
@roles_required(*STAFF)
def leave_decide(id_, action):
    if action not in ("approve", "reject"):
        return err("Thao tác không hợp lệ", 404)
    r, user = db.get("leave_requests", id_), current_user()
    if not r:
        return err("Không tìm thấy đơn nghỉ phép", 404)
    if r["status"] != "Chờ duyệt":
        return err("Đơn này đã được xử lý", 409)
    if user.get("lecturer_id") and user["lecturer_id"] == r["lecturer_id"]:
        return err("Không thể tự duyệt đơn nghỉ phép của chính mình", 403)
    note = str((request.get_json(silent=True) or {}).get("note", ""))[:300]
    status = "Đã duyệt" if action == "approve" else "Từ chối"
    r = db.update("leave_requests", id_, {"status": status, "history": r.get("history", []) + [
        {"by": user["full_name"], "action": status, "note": note, "at": now_str()}]})
    if action == "approve":
        _mark_leave_attendance(r)
    ns.notify_lecturer(r["lecturer_id"], "leave", f"Đơn nghỉ phép {id_} của bạn đã {'được duyệt' if action == 'approve' else 'bị từ chối'}", "/leave")
    audit("Duyệt đơn nghỉ phép" if action == "approve" else "Từ chối đơn nghỉ phép", target_of("leave", r))
    return jsonify(ls.enrich("leave", r, ls.Lookup()))


# ------------------------------------------------------------------ Chấm công tự phục vụ
def _my_lecturer():
    lid = current_user().get("lecturer_id")
    return lid if lid and db.get("lecturers", lid) else None


@bp.post("/attendance/check-in")
@login_required
def check_in():
    lid = _my_lecturer()
    if not lid:
        return err("Tài khoản không gắn với hồ sơ giảng viên")
    rec = db.find_one("attendance", lecturer_id=lid, date=today().isoformat())
    if rec and (rec.get("check_in") or rec["status"] == "Nghỉ phép"):
        return err("Hôm nay bạn đã chấm công hoặc đang nghỉ phép", 409)
    now = datetime.now().strftime("%H:%M")
    st = "Đi muộn" if now > ls.get_settings()["work_start"] else "Có mặt"
    if rec:
        db.update("attendance", rec["id"], {"check_in": now, "status": st})
    else:
        rec = db.insert("attendance", {"lecturer_id": lid, "date": today().isoformat(), "check_in": now, "check_out": "", "status": st, "note": "Tự chấm công"}, "CC", 5)
    audit("Chấm công vào", f"{rec['id']} ({lid})")
    return jsonify(db.get("attendance", rec["id"]))


@bp.post("/attendance/check-out")
@login_required
def check_out():
    lid = _my_lecturer()
    rec = db.find_one("attendance", lecturer_id=lid, date=today().isoformat()) if lid else None
    if not rec or not rec.get("check_in") or rec.get("check_out"):
        return err("Bạn cần chấm công vào trước, và chỉ chấm công ra một lần/ngày", 409)
    db.update("attendance", rec["id"], {"check_out": datetime.now().strftime("%H:%M")})
    audit("Chấm công ra", f"{rec['id']} ({lid})")
    return jsonify(db.get("attendance", rec["id"]))


# ------------------------------------------------------------------ Thông báo
@bp.get("/notifications")
@login_required
def notifications():
    rows = ns.for_user(current_user()["id"])
    t = request.args.get("type")
    shown = [n for n in rows if (not t or n["type"] == t) and (request.args.get("unread") != "1" or not n["read"])]
    return jsonify(items=shown[:200], unread=sum(1 for n in rows if not n["read"]), total=len(rows))


@bp.post("/notifications/read-all")
@login_required
def notif_read_all():
    uid, rows = current_user()["id"], db.all("notifications")
    for n in rows:
        if n["user_id"] == uid:
            n["read"] = True
    db.write("notifications", rows)
    return jsonify(message="Đã đánh dấu đã đọc tất cả")


@bp.post("/notifications/<id_>/read")
@login_required
def notif_read(id_):
    n = db.get("notifications", id_)
    if not n or n["user_id"] != current_user()["id"]:
        return err("Không tìm thấy thông báo", 404)
    db.update("notifications", id_, {"read": True})
    return jsonify(message="ok")


@bp.delete("/notifications/<id_>")
@login_required
def notif_delete(id_):
    n = db.get("notifications", id_)
    if not n or n["user_id"] != current_user()["id"]:
        return err("Không tìm thấy thông báo", 404)
    db.delete("notifications", id_)
    return jsonify(message="Đã xoá thông báo")


# ------------------------------------------------------------------ Tìm kiếm toàn hệ thống
@bp.get("/search")
@login_required
def search():
    q, user = fold(request.args.get("q", "")).strip(), current_user()
    if not q:
        return jsonify(lecturers=[], faculties=[], departments=[], contracts=[])
    ctx, out = ls.Lookup(), {}
    for name, key in (("lecturers", "lecturers"), ("faculties", "faculties"), ("departments", "departments"), ("contracts", "contracts")):
        cfg = RES[name]
        if user["role"] not in cfg["read"]:
            out[key] = []
            continue
        rows = [ls.enrich(name, r, ctx) for r in scope(name, db.all(cfg["file"]), user)]
        out[key] = [r for r in rows if any(q in fold(r.get(k, "")) for k in cfg["search"])][:5]
    return jsonify(out)  # scope() đã giới hạn: giảng viên chỉ tìm thấy chính mình


# ------------------------------------------------------------------ Upload ảnh đại diện
MAGIC = {".png": (b"\x89PNG",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".gif": (b"GIF8",), ".webp": (b"RIFF",)}


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return err("Chưa chọn tệp")
    ext = os.path.splitext(f.filename)[1].lower()
    data = f.read(2 * 1024 * 1024 + 1)
    if ext not in MAGIC or not data.startswith(MAGIC[ext]):
        return err("Chỉ chấp nhận ảnh PNG, JPG, GIF, WEBP hợp lệ", 422)
    if len(data) > 2 * 1024 * 1024:
        return err("Ảnh tối đa 2MB", 422)
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    name = secrets.token_hex(8) + ext
    with open(os.path.join(Config.UPLOAD_DIR, name), "wb") as out:
        out.write(data)
    return jsonify(url=f"/static/uploads/{name}")


# ------------------------------------------------------------------ Hệ thống: cài đặt, backup, import/export
@bp.get("/system/info")
@roles_required(*STAFF)
def system_info():
    size = sum(os.path.getsize(os.path.join(Config.DATA_DIR, f)) for f in os.listdir(Config.DATA_DIR) if f.endswith(".json"))
    return jsonify(settings=ls.get_settings(), data_size=size, python="3.11+", storage="JSON files (không dùng SQL)",
                   counts={n: len(db.all(n)) for n in COLLECTIONS if n != "system_settings"})


@bp.get("/system/settings")
@roles_required(*STAFF)
def get_settings():
    return jsonify(ls.get_settings())


@bp.put("/system/settings")
@roles_required(*ADM)
def put_settings():
    d, s, errors = request.get_json(silent=True) or {}, ls.get_settings(), {}
    for k in ("system_name", "school_name"):
        if k in d:
            v = str(d[k]).strip()
            if 3 <= len(v) <= 100:
                s[k] = v
            else:
                errors[k] = "Độ dài từ 3 đến 100 ký tự"
    if "contract_warning_days" in d:
        try:
            n = int(d["contract_warning_days"])
            assert 1 <= n <= 365
            s["contract_warning_days"] = n
        except (ValueError, TypeError, AssertionError):
            errors["contract_warning_days"] = "Từ 1 đến 365 ngày"
    for k in ("work_start", "work_end"):
        if k in d:
            if TIME_RE.match(str(d[k])):
                s[k] = d[k]
            else:
                errors[k] = "Giờ không hợp lệ (HH:MM)"
    if errors:
        return err("Dữ liệu không hợp lệ", 422, errors)
    db.write("system_settings", s)
    audit("Cập nhật cấu hình hệ thống", "system_settings")
    return jsonify(s)


@bp.get("/system/backups")
@roles_required(*ADM)
def backups():
    return jsonify(items=backup_service.listing())


@bp.post("/system/backup")
@roles_required(*ADM)
def backup_now():
    name = backup_service.create()
    audit("Sao lưu dữ liệu", name)
    return jsonify(name=name, message="Đã sao lưu dữ liệu"), 201


@bp.post("/system/restore")
@roles_required(*ADM)
def restore():
    name = (request.get_json(silent=True) or {}).get("name", "")
    try:
        backup_service.restore(name)
    except (ValueError, FileNotFoundError) as e:
        return err(str(e), 404 if isinstance(e, FileNotFoundError) else 422)
    audit("Khôi phục dữ liệu", name)
    return jsonify(message="Đã khôi phục dữ liệu")


@bp.delete("/system/backups/<name>")
@roles_required(*ADM)
def delete_backup(name):
    try:
        backup_service.remove(name)
    except (ValueError, FileNotFoundError) as e:
        return err(str(e), 404 if isinstance(e, FileNotFoundError) else 422)
    audit("Xoá bản sao lưu", name)
    return jsonify(message="Đã xoá bản sao lưu")


@bp.get("/system/export")
@roles_required(*ADM)
def export_json():
    audit("Export dữ liệu JSON", "all")
    body = json.dumps(backup_service.export_all(), ensure_ascii=False, indent=2)
    return Response(body, mimetype="application/json", headers={
        "Content-Disposition": f"attachment; filename=hr-export-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"})


@bp.post("/system/import")
@roles_required(*ADM)
def import_json():
    try:
        f = request.files.get("file")
        payload = json.loads(f.read().decode("utf-8")) if f else request.get_json(silent=True)
        done = backup_service.import_all(payload)
    except (ValueError, UnicodeDecodeError) as e:
        return err(f"Import thất bại: {e}", 422)
    audit("Import dữ liệu JSON", ", ".join(done))
    return jsonify(message="Đã import dữ liệu", collections=done)
