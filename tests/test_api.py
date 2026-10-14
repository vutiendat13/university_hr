"""Smoke test API + phân quyền. Chạy:  python -m unittest tests.test_api -v
Dùng thư mục dữ liệu tạm nên không ảnh hưởng data/ thật."""
import os
import tempfile
import unittest

_tmp = tempfile.mkdtemp()
os.environ["HR_DATA_DIR"] = os.path.join(_tmp, "data")
os.environ["HR_BACKUP_DIR"] = os.path.join(_tmp, "backup")

from app import app  # noqa: E402


class Client:
    def __init__(self, username=None, password=None):
        self.c = app.test_client()
        self.c.get("/login")
        with self.c.session_transaction() as s:
            self.csrf = s["csrf"]
        if username:
            r = self.c.post("/api/auth/login", json={"username": username, "password": password}, headers=self.h())
            assert r.status_code == 200, r.data
            self.csrf = r.get_json()["csrf"]

    def h(self):
        return {"X-CSRF-Token": self.csrf}

    def get(self, u): return self.c.get(u)
    def post(self, u, j=None): return self.c.post(u, json=j or {}, headers=self.h())
    def put(self, u, j): return self.c.put(u, json=j, headers=self.h())
    def delete(self, u): return self.c.delete(u, headers=self.h())


LEC = dict(id="GV900", full_name="Nguyễn Test", dob="1990-05-01", gender="Nam", cccd="031123456789", email="test900@dhhp.demo",
           phone="0912345678", address="Hải Phòng", faculty_id="CNTT", department_id="PM", position="Giảng viên",
           degree="Thạc sĩ", join_date="2018-09-01", contract_type="Chính thức")


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin, cls.mgr, cls.lec = Client("admin", "Admin@123"), Client("manager", "Manager@123"), Client("lecturer", "Lecturer@123")

    def test_auth(self):
        anon = Client()
        self.assertEqual(anon.get("/api/lecturers").status_code, 401)
        self.assertEqual(anon.get("/dashboard").status_code, 302)
        r = anon.post("/api/auth/login", {"username": "admin", "password": "sai"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(app.test_client().post("/api/auth/login", json={"username": "admin", "password": "Admin@123"}).status_code, 400)  # thiếu CSRF
        self.assertNotIn("Admin@123", open(os.path.join(os.environ["HR_DATA_DIR"], "users.json")).read())

    def test_pages_all_roles(self):
        for cl, bad in ((self.admin, []), (self.mgr, ["/audit-logs"]), (self.lec, ["/audit-logs", "/lecturers", "/faculties", "/contracts", "/departments"])):
            for p in ["/dashboard", "/lecturers", "/faculties", "/departments", "/contracts", "/attendance", "/leave", "/evaluations",
                      "/notifications", "/audit-logs", "/settings"]:
                self.assertEqual(cl.get(p).status_code, 403 if p in bad else 200, p)
        self.assertEqual(self.lec.get("/lecturers/GV002").status_code, 403)
        self.assertEqual(self.lec.get("/me").status_code, 302)
        self.assertEqual(self.admin.get("/khong-co").status_code, 404)

    def test_read_endpoints(self):
        for u in ["lecturers", "faculties", "departments", "contracts", "attendance", "leave", "evaluations", "users", "audit-logs"]:
            r = self.admin.get(f"/api/{u}?per_page=5&q=a")
            self.assertEqual(r.status_code, 200, u)
        for u in ["dashboard/stats", "dashboard/campus", "dashboard/me", "meta", "notifications", "search?q=cntt", "system/info",
                  "system/settings", "system/backups", "lecturers/GV001/profile", "lecturers/export.csv", "system/export"]:
            self.assertEqual(self.admin.get(f"/api/{u}").status_code, 200, u)
        self.assertEqual(self.admin.get("/api/lecturers?q=nguyen").get_json()["total"] > 0, True)
        self.assertGreaterEqual(self.admin.get("/api/search?q=CNTT").get_json()["faculties"].__len__(), 1)

    def test_authorization(self):
        self.assertEqual(self.lec.get("/api/users").status_code, 403)
        self.assertEqual(self.mgr.get("/api/users").status_code, 403)
        self.assertEqual(self.mgr.get("/api/audit-logs").status_code, 403)
        self.assertEqual(self.mgr.post("/api/system/backup").status_code, 403)
        self.assertEqual(self.mgr.delete("/api/lecturers/GV003").status_code, 403)
        self.assertEqual(self.mgr.post("/api/faculties", {"id": "XX", "name": "Khoa X", "status": "Hoạt động"}).status_code, 403)
        self.assertEqual(self.lec.post("/api/lecturers", LEC).status_code, 403)
        self.assertEqual(self.lec.get("/api/lecturers/GV002").status_code, 404)  # không thấy dữ liệu người khác
        rows = self.lec.get("/api/lecturers").get_json()
        self.assertEqual([r["id"] for r in rows["items"]], ["GV001"])
        self.assertTrue(all(r["lecturer_id"] == "GV001" for r in self.lec.get("/api/attendance?per_page=100").get_json()["items"]))
        self.assertEqual(self.lec.get("/api/lecturers/GV002/profile").status_code, 403)
        self.assertEqual(self.lec.get("/api/dashboard/stats").status_code, 403)
        self.assertEqual(self.lec.put("/api/lecturers/GV002", {"phone": "0911111111"}).status_code, 404)
        self.assertEqual(self.lec.put("/api/lecturers/GV001", {"position": "Trưởng khoa"}).status_code, 403)  # trường không được tự sửa
        self.assertEqual(self.lec.put("/api/lecturers/GV001", {"phone": "0911111111"}).status_code, 200)
        self.assertEqual(self.lec.post("/api/leave/NP001/approve").status_code, 403)

    def test_lecturer_crud_validation(self):
        bad = dict(LEC, id="GV901", email="sai-email", phone="123", cccd="12", department_id="KTKT")
        r = self.admin.post("/api/lecturers", bad)
        self.assertEqual(r.status_code, 422)
        self.assertTrue({"email", "phone", "cccd", "department_id"} <= set(r.get_json()["errors"]))
        self.assertEqual(self.admin.post("/api/lecturers", dict(LEC, id="GV001")).status_code, 422)  # trùng mã
        self.assertEqual(self.mgr.post("/api/lecturers", LEC).status_code, 201)
        self.assertEqual(self.mgr.put("/api/lecturers/GV900", {"degree": "Tiến sĩ"}).get_json()["degree"], "Tiến sĩ")
        self.assertEqual(self.admin.post("/api/contracts", {"lecturer_id": "GV900", "type": "Hợp đồng 1 năm", "start_date": "2026-01-01"}).status_code, 422)
        self.assertEqual(self.admin.post("/api/contracts", {"lecturer_id": "GV900", "type": "Biên chế", "start_date": "2018-09-01"}).status_code, 201)
        self.assertEqual(self.admin.delete("/api/faculties/CNTT").status_code, 409)
        self.assertEqual(self.admin.delete("/api/lecturers/GV900").status_code, 200)
        self.assertEqual(self.admin.get("/api/contracts?lecturer_id=GV900").get_json()["total"], 0)  # xoá dây chuyền
        self.assertTrue(any(l["action"] == "Xoá giảng viên" for l in self.admin.get("/api/audit-logs").get_json()["items"]))

    def test_leave_flow(self):
        r = self.lec.post("/api/leave", {"type": "Nghỉ ốm", "from_date": "2027-03-01", "to_date": "2027-03-02", "reason": "Bị cảm cúm"})
        self.assertEqual(r.status_code, 201, r.data)
        lv = r.get_json()
        self.assertEqual((lv["status"], lv["lecturer_id"]), ("Chờ duyệt", "GV001"))
        self.assertEqual(self.lec.post("/api/leave", {"type": "Nghỉ ốm", "from_date": "2027-03-02", "to_date": "2027-03-03", "reason": "Trùng ngày"}).status_code, 422)
        self.assertEqual(self.mgr.post(f"/api/leave/{lv['id']}/approve", {"note": "ok"}).status_code, 200)
        self.assertEqual(self.mgr.post(f"/api/leave/{lv['id']}/reject").status_code, 409)
        self.assertEqual(self.mgr.get(f"/api/leave/{lv['id']}").get_json()["history"][0]["action"], "Đã duyệt")
        notes = self.lec.get("/api/notifications").get_json()
        self.assertTrue(any(lv["id"] in n["message"] for n in notes["items"]))
        self.assertEqual(self.lec.post("/api/notifications/read-all").status_code, 200)
        self.assertEqual(self.lec.get("/api/notifications").get_json()["unread"], 0)

    def test_attendance_and_evaluation(self):
        r = self.lec.post("/api/attendance/check-in")
        self.assertIn(r.status_code, (200, 409))
        self.assertIn(self.lec.post("/api/attendance/check-out").status_code, (200, 409))
        ev = {"lecturer_id": "GV005", "period": "Kỳ test", "expertise": 5, "teaching": 5, "attitude": 4, "research": 4, "contribution": 5, "discipline": 5}
        r = self.mgr.post("/api/evaluations", ev)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.get_json()["avg"], r.get_json()["grade"]), (4.67, "Xuất sắc"))
        self.assertEqual(self.mgr.post("/api/evaluations", dict(ev, expertise=9)).status_code, 422)
        self.assertEqual(self.mgr.put(f"/api/evaluations/{r.get_json()['id']}", {"expertise": 3, "teaching": 3}).get_json()["grade"], "Tốt")

    def test_users_and_system(self):
        self.assertEqual(self.admin.post("/api/users", {"username": "user1", "full_name": "User 1", "role": "MANAGER", "password": "yeu"}).status_code, 422)
        r = self.admin.post("/api/users", {"username": "user1", "full_name": "User 1", "role": "MANAGER", "password": "Matkhau1"})
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("password_hash", r.get_json())
        self.assertEqual(Client("user1", "Matkhau1").get("/api/users").status_code, 403)
        self.assertEqual(self.admin.delete("/api/users/U001").status_code, 409)  # không xoá chính mình
        self.assertEqual(self.admin.post("/api/system/backup").status_code, 201)
        name = self.admin.get("/api/system/backups").get_json()["items"][0]["name"]
        self.assertEqual(self.admin.post("/api/system/restore", {"name": "../../etc"}).status_code, 422)
        self.assertEqual(self.admin.post("/api/system/restore", {"name": name}).status_code, 200)
        exp = self.admin.get("/api/system/export").get_json()
        self.assertEqual(self.admin.post("/api/system/import", {"lecturers": [{"x": 1}]}).status_code, 422)
        self.assertEqual(self.admin.post("/api/system/import", exp).status_code, 200)
        self.assertEqual(self.admin.put("/api/system/settings", {"contract_warning_days": 45}).status_code, 200)
        self.assertEqual(self.mgr.put("/api/system/settings", {"contract_warning_days": 45}).status_code, 403)
        self.assertEqual(self.lec.post("/api/auth/change-password", {"current": "x", "new": "Abcdef12"}).status_code, 422)
        self.assertEqual(self.lec.post("/api/auth/forgot", {"username": "admin"}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
