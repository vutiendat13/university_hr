"""Nghiệp vụ giảng viên: làm giàu dữ liệu (tên khoa, trạng thái...), thống kê dashboard, hồ sơ tổng hợp."""
import re
from collections import Counter
from datetime import date, timedelta

import config as C
from services.data_manager import db
from utils.helpers import today
from utils.validators import parse_date


def get_settings():
    return {**C.DEFAULT_SETTINGS, **db.read("system_settings", {})}


def contract_status(c, warn_days):
    end = parse_date(c.get("end_date"))
    if not end:
        return "Đang hiệu lực"
    left = (end - today()).days
    return "Đã hết hạn" if left < 0 else "Sắp hết hạn" if left <= warn_days else "Đang hiệu lực"


def grade_of(avg):
    return next(name for limit, name in C.GRADES if avg >= limit)


class Lookup:
    """Nạp 1 lần các bảng tham chiếu để enrich nhiều bản ghi mà không đọc file lặp lại."""

    def __init__(self):
        t = today().isoformat()
        self.settings = get_settings()
        self.warn = int(self.settings["contract_warning_days"])
        self.fac = {f["id"]: f for f in db.all("faculties")}
        self.dep = {d["id"]: d for d in db.all("departments")}
        lects = db.all("lecturers")
        self.lec = {l["id"]: l for l in lects}
        self.on_leave = {r["lecturer_id"] for r in db.all("leave_requests")
                         if r["status"] == "Đã duyệt" and r["from_date"] <= t <= r["to_date"]}
        active = [l for l in lects if l.get("work_status") != "Đã nghỉ việc"]
        self.fac_count = Counter(l["faculty_id"] for l in active)
        self.dep_count = Counter(l["department_id"] for l in active)
        self.dep_per_fac = Counter(d["faculty_id"] for d in self.dep.values())


def age_of(dob):
    d = parse_date(dob)
    return int((today() - d).days // 365.25) if d else None


def enrich(res, item, ctx):
    o = dict(item)
    if res == "lecturers":
        o["faculty_name"] = ctx.fac.get(o.get("faculty_id"), {}).get("name", "")
        o["department_name"] = ctx.dep.get(o.get("department_id"), {}).get("name", "")
        o["status"] = ("Đã nghỉ việc" if o.get("work_status") == "Đã nghỉ việc"
                       else "Đang nghỉ phép" if o["id"] in ctx.on_leave else "Đang làm việc")
        o["age"] = age_of(o.get("dob"))
    elif res == "faculties":
        o["lecturer_count"] = ctx.fac_count.get(o["id"], 0)
        o["department_count"] = ctx.dep_per_fac.get(o["id"], 0)
    elif res == "departments":
        o["faculty_name"] = ctx.fac.get(o.get("faculty_id"), {}).get("name", "")
        o["lecturer_count"] = ctx.dep_count.get(o["id"], 0)
    elif res == "users":
        o.pop("password_hash", None)
        o["lecturer_name"] = ctx.lec.get(o.get("lecturer_id"), {}).get("full_name", "")
    elif "lecturer_id" in o:
        l = ctx.lec.get(o["lecturer_id"], {})
        o["lecturer_name"] = l.get("full_name", "(đã xoá)")
        o["faculty_id"] = l.get("faculty_id", "")
        o["faculty_name"] = ctx.fac.get(l.get("faculty_id"), {}).get("name", "")
        if res == "contracts":
            o["status"] = contract_status(o, ctx.warn)
            e = parse_date(o.get("end_date"))
            o["days_left"] = (e - today()).days if e else None
        if res == "evaluations":
            o["criteria"] = {k: o.get(k) for k in C.CRITERIA}
    return o


# ------------------------------------------------------------------ thống kê dashboard
def campus_data():
    """Dữ liệu tổng hợp theo khoa (đếm, trình độ) cho cảnh 3D. Chỉ là số liệu gộp, không lộ hồ sơ cá nhân."""
    ctx = Lookup()
    out = []
    for f in ctx.fac.values():
        ls = [l for l in ctx.lec.values() if l["faculty_id"] == f["id"] and l.get("work_status") != "Đã nghỉ việc"]
        out.append({"id": f["id"], "name": f["name"], "total": len(ls),
                    "degrees": {d: sum(1 for l in ls if l["degree"] == d) for d in C.DEGREES}})
    return out


def dashboard_stats():
    ctx = Lookup()
    lects = [l for l in ctx.lec.values() if l.get("work_status") != "Đã nghỉ việc"]
    total, on_leave = len(lects), len([l for l in lects if l["id"] in ctx.on_leave])
    official = sum(1 for l in lects if l["contract_type"] == "Chính thức")
    ages = [age_of(l["dob"]) or 0 for l in lects]
    buckets = {"< 30": sum(a < 30 for a in ages), "30 - 40": sum(30 <= a < 40 for a in ages),
               "40 - 50": sum(40 <= a < 50 for a in ages), "> 50": sum(a >= 50 for a in ages)}
    contracts = [enrich("contracts", c, ctx) for c in db.all("contracts")]
    expiring = sorted([c for c in contracts if c["status"] == "Sắp hết hạn"], key=lambda c: c["end_date"])
    pending = [enrich("leave", r, ctx) for r in db.all("leave_requests") if r["status"] == "Chờ duyệt"]
    return {
        "cards": {"total": total, "official": official, "contract": total - official,
                  "faculties": len(ctx.fac), "departments": len(ctx.dep),
                  "on_leave": on_leave, "working": total - on_leave},
        "by_faculty": [{"id": f["id"], "name": f["name"], "count": ctx.fac_count.get(f["id"], 0)} for f in ctx.fac.values()],
        "gender": {g: sum(1 for l in lects if l["gender"] == g) for g in C.GENDERS},
        "ages": buckets,
        "degrees": {d: sum(1 for l in lects if l["degree"] == d) for d in C.DEGREES},
        "expiring_contracts": expiring[:6], "expiring_total": len(expiring),
        "expired_total": sum(1 for c in contracts if c["status"] == "Đã hết hạn"),
        "pending_leave": sorted(pending, key=lambda r: r["created_at"], reverse=True)[:6],
        "pending_total": len(pending),
        "activities": sorted(db.all("audit_logs"), key=lambda a: a["timestamp"], reverse=True)[:8],
    }


def my_summary(lecturer_id):
    """Tóm tắt cá nhân + lịch làm việc tuần này (từ bản ghi chấm công) cho Giảng viên."""
    ctx = Lookup()
    t = today()
    month = t.strftime("%Y-%m")
    att = [a for a in db.all("attendance") if a["lecturer_id"] == lecturer_id]
    by_date = {a["date"]: a for a in att}
    monday = t - timedelta(days=t.weekday())
    week = []
    for i in range(5):
        d = monday + timedelta(days=i)
        a = by_date.get(d.isoformat())
        week.append({"date": d.isoformat(), "weekday": ["T2", "T3", "T4", "T5", "T6"][i], "today": d == t,
                     "status": a["status"] if a else ("Chưa đến" if d > t else "Chưa chấm công"),
                     "check_in": a.get("check_in", "") if a else "", "check_out": a.get("check_out", "") if a else ""})
    evals = sorted([e for e in db.all("evaluations") if e["lecturer_id"] == lecturer_id], key=lambda e: e["created_at"], reverse=True)
    leaves = [r for r in db.all("leave_requests") if r["lecturer_id"] == lecturer_id]
    contract = next(iter(sorted([enrich("contracts", c, ctx) for c in db.all("contracts") if c["lecturer_id"] == lecturer_id],
                                key=lambda c: c["start_date"], reverse=True)), None)
    return {"month_present": sum(1 for a in att if a["date"].startswith(month) and a["status"] in ("Có mặt", "Đi muộn")),
            "month_late": sum(1 for a in att if a["date"].startswith(month) and a["status"] == "Đi muộn"),
            "pending_leave": sum(1 for r in leaves if r["status"] == "Chờ duyệt"),
            "latest_eval": evals[0] if evals else None, "contract": contract, "week": week,
            "today_record": by_date.get(t.isoformat()), "settings": {"work_start": ctx.settings["work_start"], "work_end": ctx.settings["work_end"]}}


def profile(lecturer_id, is_admin):
    """Hồ sơ tổng hợp cho trang chi tiết (7 tab)."""
    ctx = Lookup()
    l = ctx.lec.get(lecturer_id)
    if not l:
        return None
    mine = lambda res, rows: sorted([enrich(res, r, ctx) for r in rows if r["lecturer_id"] == lecturer_id],
                                    key=lambda r: r.get("date") or r.get("start_date") or r.get("from_date") or r.get("created_at"), reverse=True)
    pat = re.compile(rf"\b{re.escape(lecturer_id)}\b")
    history = [a for a in db.all("audit_logs") if pat.search(a["target"])]
    if not is_admin:
        history = [{k: v for k, v in h.items() if k != "ip"} for h in history]
    jd = parse_date(l.get("join_date"))
    return {"lecturer": enrich("lecturers", l, ctx),
            "seniority_years": round((today() - jd).days / 365.25, 1) if jd else None,
            "contracts": mine("contracts", db.all("contracts")),
            "attendance": mine("attendance", db.all("attendance"))[:60],
            "leave": mine("leave", db.all("leave_requests")),
            "evaluations": mine("evaluations", db.all("evaluations")),
            "history": sorted(history, key=lambda h: h["timestamp"], reverse=True)[:40]}
