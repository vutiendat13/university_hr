"""Sinh dữ liệu demo (tên/thông tin hư cấu). Chạy:  python -m utils.seed_data --force
Tự động được gọi khi khởi động nếu thư mục data/ chưa có dữ liệu."""
import random
import sys
import unicodedata
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

import config as C
from services.data_manager import COLLECTIONS, db

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô", "Dương", "Phan", "Lý", "Đinh"]
DEM_NAM = ["Văn", "Hữu", "Minh", "Quang", "Đức", "Xuân", "Thành", "Công"]
TEN_NAM = ["An", "Nam", "Hùng", "Dũng", "Long", "Tuấn", "Hải", "Phong", "Khánh", "Sơn", "Bình", "Cường", "Đạt",
           "Thắng", "Trung", "Quân", "Việt", "Hiếu", "Kiên", "Lâm", "Toàn", "Huy", "Thịnh", "Đông"]
DEM_NU = ["Thị", "Ngọc", "Thu", "Thanh", "Phương", "Khánh", "Bích", "Diệu"]
TEN_NU = ["Mai", "Hương", "Lan", "Linh", "Hà", "Thảo", "Ngân", "Trang", "Hạnh", "Oanh", "Yến", "Nhung", "Hoa",
          "Dung", "Thủy", "Vân", "Huyền", "Loan", "Nga", "Chi", "Quỳnh", "Ly", "Thơm", "Hồng"]
ADDR = ["Số {n} phố Lạch Tray, quận Ngô Quyền", "Số {n} phố Lê Lợi, quận Ngô Quyền", "Số {n} đường Nguyễn Văn Linh, quận Lê Chân",
        "Số {n} phố Trần Nguyên Hãn, quận Lê Chân", "Số {n} phố Hoàng Diệu, quận Hồng Bàng", "Số {n} đường Phạm Văn Đồng, quận Kiến An",
        "Số {n} đường Cát Dài, quận Lê Chân", "Số {n} phố Điện Biên Phủ, quận Hồng Bàng"]

FACULTIES = [("CNTT", "Khoa Công nghệ thông tin"), ("KT", "Khoa Kinh tế"), ("NN", "Khoa Ngoại ngữ"),
             ("DDT", "Khoa Điện – Điện tử"), ("CK", "Khoa Cơ khí"), ("SP", "Khoa Sư phạm")]
DEPARTMENTS = [("PM", "Công nghệ phần mềm", "CNTT"), ("HTTT", "Hệ thống thông tin", "CNTT"), ("MMT", "Mạng máy tính", "CNTT"),
               ("KHMT", "Khoa học máy tính", "CNTT"), ("QTKD", "Quản trị kinh doanh", "KT"), ("KTKT", "Kế toán – Kiểm toán", "KT"),
               ("TCNH", "Tài chính – Ngân hàng", "KT"), ("TA", "Tiếng Anh", "NN"), ("TQ", "Tiếng Trung", "NN"),
               ("DCN", "Điện công nghiệp", "DDT"), ("DTVT", "Điện tử – Viễn thông", "DDT"), ("CKCT", "Cơ khí chế tạo", "CK"),
               ("CDT", "Cơ điện tử", "CK"), ("GDTH", "Giáo dục tiểu học", "SP")]


def slug(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().replace(" ", "")


def ts(d, hh=8, mm=0):
    return datetime(d.year, d.month, d.day, hh, mm).strftime("%Y-%m-%d %H:%M:%S")


def weekdays_back(n, start):
    out, d = [], start
    while len(out) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            out.append(d)
    return out


def build(today=None):
    R = random.Random(2026)
    today = today or date.today()
    fixed = [("Nguyễn Văn An", "Nam"), ("Trần Thị Mai", "Nữ"), ("Phạm Văn Nam", "Nam"), ("Lê Thị Hương", "Nữ")]
    names, seen = list(fixed), {n for n, _ in fixed}
    while len(names) < 58:
        g = R.choice(["Nam", "Nữ"])
        n = f"{R.choice(HO)} {R.choice(DEM_NAM if g == 'Nam' else DEM_NU)} {R.choice(TEN_NAM if g == 'Nam' else TEN_NU)}"
        if n not in seen:
            seen.add(n); names.append((n, g))

    faculties = [{"id": i, "name": n, "dean": "", "status": "Hoạt động", "description": f"{n} - Trường Đại học Hải Phòng"} for i, n in FACULTIES]
    departments = [{"id": i, "name": n, "faculty_id": f, "head": ""} for i, n, f in DEPARTMENTS]

    lecturers = []
    for idx, (name, gender) in enumerate(names, 1):
        dep = DEPARTMENTS[(idx - 1) % len(DEPARTMENTS)]
        dob = date(R.randint(1966, 1999), R.randint(1, 12), R.randint(1, 28))
        jd = date(R.randint(dob.year + 24, 2025), R.randint(1, 12), R.randint(1, 28))
        code = f"GV{idx:03d}"
        ct = R.choices(C.LECTURER_CONTRACT_TYPES, [60, 30, 10])[0]
        lecturers.append({
            "id": code, "full_name": name, "gender": gender, "dob": dob.isoformat(),
            "cccd": f"031{R.randint(0, 10**9 - 1):09d}", "email": f"{slug(name.split()[-1])}.{code.lower()}@dhhp.demo",
            "phone": f"09{R.randint(0, 10**8 - 1):08d}", "address": R.choice(ADDR).format(n=R.randint(1, 250)) + ", Hải Phòng",
            "faculty_id": dep[2], "department_id": dep[0], "position": R.choices(["Giảng viên", "Giảng viên chính", "Trợ giảng"], [60, 28, 12])[0],
            "degree": R.choices(C.DEGREES, [8, 28, 14, 4, 2])[0], "join_date": jd.isoformat(), "contract_type": ct,
            "work_status": "Đang làm việc", "avatar": ""})
    # Trưởng khoa / trưởng bộ môn: người đầu tiên của mỗi khoa / bộ môn (nâng tối thiểu lên Tiến sĩ)
    for f in faculties:
        head = next(l for l in lecturers if l["faculty_id"] == f["id"] and l["position"] != "Trưởng bộ môn")
        head.update(position="Trưởng khoa", degree=head["degree"] if head["degree"] in ("PGS", "GS") else "Tiến sĩ", contract_type="Chính thức")
        f["dean"] = head["full_name"]
    for d in departments:
        pool = [l for l in lecturers if l["department_id"] == d["id"] and l["position"] not in ("Trưởng khoa", "Trưởng bộ môn")]
        pool[0].update(position="Trưởng bộ môn", degree="Tiến sĩ" if pool[0]["degree"] in ("Cử nhân", "Thạc sĩ") else pool[0]["degree"], contract_type="Chính thức")
        d["head"] = pool[0]["full_name"]
    lecturers[8]["work_status"] = "Đã nghỉ việc"
    lecturers[8]["contract_type"] = "Hợp đồng"

    # Hợp đồng: 1 hợp đồng / giảng viên; cố ý tạo vài hợp đồng sắp hết hạn & đã hết hạn để demo cảnh báo
    contracts, n_soon, n_exp = [], 0, 0
    for l in lecturers:
        jd = date.fromisoformat(l["join_date"])
        cid = f"HD{len(contracts) + 1:03d}"
        if l["contract_type"] == "Chính thức":
            c = {"type": "Biên chế", "start_date": jd.isoformat(), "end_date": ""}
        else:
            kind = "Thỉnh giảng" if l["contract_type"] == "Thỉnh giảng" else R.choice(["Hợp đồng 1 năm", "Hợp đồng 3 năm"])
            span = {"Thỉnh giảng": 180, "Hợp đồng 1 năm": 365, "Hợp đồng 3 năm": 1095}[kind]
            roll = R.random()
            end = (today + timedelta(days=R.randint(8, 55)) if roll < .25 and n_soon < 6 else
                   today - timedelta(days=R.randint(10, 120)) if roll < .35 and n_exp < 3 else
                   today + timedelta(days=R.randint(90, 600)))
            n_soon += 8 <= (end - today).days <= 55
            n_exp += end < today
            c = {"type": kind, "start_date": (end - timedelta(days=span)).isoformat(), "end_date": end.isoformat()}
        contracts.append({"id": cid, "lecturer_id": l["id"], "note": "Hợp đồng làm việc tại trường", **c})

    # Chấm công: 20 giảng viên x 8 ngày làm việc gần nhất (GV001 luôn có để demo tài khoản lecturer)
    attendance = []
    for l in lecturers[:20]:
        for d in weekdays_back(8, today):
            st = R.choices(C.ATTENDANCE_STATUS, [80, 10, 4, 6])[0]
            ci = co = ""
            if st == "Có mặt":
                ci, co = f"07:{R.randint(0, 29):02d}", f"{R.randint(16, 17)}:{R.randint(0, 59):02d}"
            elif st == "Đi muộn":
                ci, co = f"0{R.randint(7, 8)}:{R.randint(35, 59):02d}", f"{R.randint(16, 17)}:{R.randint(30, 59):02d}"
            attendance.append({"id": f"CC{len(attendance) + 1:05d}", "lecturer_id": l["id"], "date": d.isoformat(),
                               "check_in": ci, "check_out": co, "status": st,
                               "note": {"Vắng": "Không báo trước", "Nghỉ phép": "Nghỉ có đơn", "Đi muộn": "Kẹt xe"}.get(st, "")})

    # Đơn nghỉ phép
    leaves, reasons = [], ["Việc gia đình", "Khám sức khoẻ định kỳ", "Về quê giải quyết việc riêng", "Tham dự hội thảo", "Chăm sóc người thân ốm", "Nghỉ phép năm"]
    approvers = ["Quản lý Nhân sự", "Quản trị viên"]
    pool = [l for l in lecturers if l["work_status"] == "Đang làm việc"]
    for i in range(24):
        l = pool[(i * 2 + 1) % len(pool)] if i else lecturers[0]
        start = today + timedelta(days=R.randint(-40, 30))
        end = start + timedelta(days=R.randint(0, 4))
        if i in (1, 2):
            start, end = today - timedelta(days=1), today + timedelta(days=2)
            l = lecturers[10 + i]
        status = "Đã duyệt" if i in (1, 2) else R.choices(C.LEAVE_STATUS, [35, 45, 20])[0]
        created = min(start, today) - timedelta(days=R.randint(2, 7))
        hist = [] if status == "Chờ duyệt" else [{"by": R.choice(approvers), "action": status, "note": "", "at": ts(created + timedelta(days=1), 9, 30)}]
        leaves.append({"id": f"NP{i + 1:03d}", "lecturer_id": l["id"], "type": R.choice(C.LEAVE_TYPES[:3]),
                       "from_date": start.isoformat(), "to_date": end.isoformat(), "reason": R.choice(reasons),
                       "status": status, "history": hist, "created_at": ts(created, 8, 15)})
    # chặn trùng khoảng ngày của cùng giảng viên
    seen_rng, clean = {}, []
    for r in leaves:
        if any(r["from_date"] <= o["to_date"] and o["from_date"] <= r["to_date"] for o in seen_rng.get(r["lecturer_id"], [])):
            continue
        seen_rng.setdefault(r["lecturer_id"], []).append(r); clean.append(r)
    leaves = clean

    # Đánh giá: năm học hiện tại cho tất cả + năm học trước cho 12 người
    evaluations = []
    for per, subset in (("Năm học 2025-2026", lecturers), ("Năm học 2024-2025", lecturers[:12])):
        for l in subset:
            sc = {k: R.choices([2, 3, 4, 5], [4, 22, 48, 26])[0] for k in C.CRITERIA}
            avg = round(sum(sc.values()) / len(sc), 2)
            grade = next(n for lim, n in C.GRADES if avg >= lim)
            evaluations.append({"id": f"DG{len(evaluations) + 1:03d}", "lecturer_id": l["id"], "period": per, **sc, "avg": avg, "grade": grade,
                                "comment": R.choice(["Hoàn thành tốt nhiệm vụ được giao.", "Cần tăng cường công bố nghiên cứu.", "Nhiệt tình, có trách nhiệm với sinh viên.", "Đóng góp tích cực cho hoạt động của bộ môn."]),
                                "evaluator": "Quản lý Nhân sự", "created_at": ts(today - timedelta(days=R.randint(10, 200) if per.endswith("2026") else R.randint(400, 700)), 15)})

    users = [
        {"id": "U001", "username": "admin", "password_hash": generate_password_hash("Admin@123"), "full_name": "Quản trị viên", "role": "ADMIN", "email": "admin@dhhp.demo", "lecturer_id": "", "active": True},
        {"id": "U002", "username": "manager", "password_hash": generate_password_hash("Manager@123"), "full_name": "Quản lý Nhân sự", "role": "MANAGER", "email": "manager@dhhp.demo", "lecturer_id": "", "active": True},
        {"id": "U003", "username": "lecturer", "password_hash": generate_password_hash("Lecturer@123"), "full_name": lecturers[0]["full_name"], "role": "LECTURER", "email": lecturers[0]["email"], "lecturer_id": "GV001", "active": True},
    ]
    notifications = [
        {"id": "TB00001", "user_id": "U001", "type": "system", "message": "Chào mừng đến với Hệ thống quản lý nhân sự giảng viên", "link": "", "read": False, "created_at": ts(today), "key": None},
        {"id": "TB00002", "user_id": "U003", "type": "evaluation", "message": "Bạn có đánh giá mới: Năm học 2025-2026", "link": "/evaluations", "read": False, "created_at": ts(today - timedelta(days=1)), "key": None},
        {"id": "TB00003", "user_id": "U003", "type": "leave", "message": "Đơn nghỉ phép của bạn đã được xử lý", "link": "/leave", "read": True, "created_at": ts(today - timedelta(days=3)), "key": None},
    ]
    logs = [{"id": f"LOG{i + 1:05d}", "user": u, "role": r, "action": a, "target": t, "timestamp": ts(today - timedelta(days=9 - i), 9, i * 3), "ip": "127.0.0.1"}
            for i, (u, r, a, t) in enumerate([
                ("admin", "ADMIN", "Đăng nhập", "-"), ("admin", "ADMIN", "Thêm giảng viên", "GV050"), ("manager", "MANAGER", "Sửa giảng viên", "GV002"),
                ("manager", "MANAGER", "Duyệt đơn nghỉ phép", "NP003 (GV011)"), ("admin", "ADMIN", "Sao lưu dữ liệu", "backup"),
                ("admin", "ADMIN", "Xoá bộ môn", "BM-CU"), ("manager", "MANAGER", "Thêm đánh giá", "DG010 (GV010)"), ("admin", "ADMIN", "Đăng nhập", "-")])]
    return {"users": users, "lecturers": lecturers, "faculties": faculties, "departments": departments, "contracts": contracts,
            "attendance": attendance, "leave_requests": leaves, "evaluations": evaluations, "notifications": notifications,
            "audit_logs": logs, "system_settings": dict(C.DEFAULT_SETTINGS)}


def seed(force=False):
    if not force and db.exists("users") and db.read("users"):
        return False
    for name, data in build().items():
        db.write(name, data)
    return True


if __name__ == "__main__":
    print("Đã tạo dữ liệu demo." if seed("--force" in sys.argv) else "Đã có dữ liệu. Dùng --force để tạo lại (sẽ ghi đè!).")
