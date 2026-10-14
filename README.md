# Hệ thống quản lý nhân sự giảng viên – Đại học Hải Phòng

Ứng dụng web full-stack quản lý hồ sơ, hợp đồng, chấm công, nghỉ phép và đánh giá giảng viên.
Dự án phục vụ **học tập, đồ án và portfolio**. Toàn bộ dữ liệu lưu bằng **file JSON** – *không dùng SQL/database server*.

## Mục tiêu
- Mô phỏng một hệ thống nhân sự đại học thực tế với phân quyền 3 vai trò.
- Cấu trúc code rõ ràng (Blueprint + service layer + DataManager), dễ đọc, dễ thuyết trình, dễ mở rộng.

## Tính năng
| Nhóm | Chức năng |
|---|---|
| Xác thực | Đăng nhập session, ghi nhớ đăng nhập, khoá tạm sau 5 lần sai, quên mật khẩu (gửi yêu cầu cho Admin), đổi mật khẩu |
| Phân quyền | ADMIN / MANAGER / LECTURER – kiểm tra ở **backend** cho cả trang và API |
| Dashboard | 7 thẻ thống kê, 4 biểu đồ (khoa, giới tính, độ tuổi, trình độ), **campus 3D** (Three.js) bấm vào toà nhà xem số liệu khoa, hợp đồng sắp hết hạn, duyệt nhanh nghỉ phép, hoạt động gần đây |
| Giảng viên | CRUD, hồ sơ 7 tab, upload ảnh, tìm kiếm không dấu, bộ lọc, sắp xếp, phân trang, export CSV |
| Khoa / Bộ môn | CRUD, xem cây bộ môn, xem giảng viên theo khoa/bộ môn |
| Hợp đồng | CRUD, trạng thái tự tính (Đang hiệu lực / Sắp hết hạn / Đã hết hạn), cảnh báo + thông báo tự động |
| Chấm công | CRUD (Admin), giảng viên tự chấm công vào/ra, lọc theo ngày/tháng/khoa/giảng viên |
| Nghỉ phép | Giảng viên gửi đơn; Manager/Admin duyệt/từ chối, lưu lịch sử xử lý, tự điền chấm công "Nghỉ phép" |
| Đánh giá | 6 tiêu chí (1–5), tự tính điểm trung bình + xếp loại |
| Thông báo | Chuông + trang riêng, đã đọc/chưa đọc, lọc theo loại |
| Hệ thống | Audit log (user, action, target, timestamp, ip), backup/restore, import/export JSON, cấu hình, quản lý tài khoản |
| UI/UX | Dark mode (lưu localStorage), responsive + menu hamburger, toast, skeleton loading, modal, GSAP animation, trang 403/404/500 |

## Công nghệ
- **Backend:** Python 3.11+, Flask, Blueprints, Jinja2, REST API, session auth, Werkzeug password hashing, JSON storage.
- **Frontend:** HTML5, CSS3, JavaScript ES6+ (không framework), Three.js r128, GSAP 3, Chart.js 4, Font Awesome 6 (tải qua CDN cdnjs).

> ⚠️ Giao diện cần **kết nối Internet** để tải thư viện từ CDN (Three.js, GSAP, Chart.js, Font Awesome, Google Fonts). Muốn chạy offline, tải các file đó về `static/vendor/` và sửa đường dẫn trong `templates/base.html`, `login.html`, `dashboard.html`.

## Kiến trúc
```
Browser (HTML/CSS/JS) ──fetch JSON + CSRF token──▶ routes/api.py ─┐
        ▲                                                         ├─▶ services/* (nghiệp vụ) ─▶ DataManager ─▶ data/*.json
        └── Jinja2 pages ◀── routes/dashboard.py, routes/auth.py ─┘
```
- `services/data_manager.py` là **nơi duy nhất** đọc/ghi JSON (khoá luồng, ghi atomic, sinh ID, tìm/lọc, backup).
- `routes/api.py` dùng bảng quyền `RES` để dựng CRUD cho mọi resource; nghiệp vụ đặc thù là endpoint riêng.
- Quan hệ dữ liệu bằng ID tham chiếu (`faculty_id`, `department_id`, `lecturer_id`).

## Cài đặt & chạy
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
Mở: **http://127.0.0.1:5000**

Lần chạy đầu nếu `data/` trống, hệ thống tự sinh dữ liệu demo. Sinh lại từ đầu (ghi đè!): `python -m utils.seed_data --force`
(dữ liệu hợp đồng/chấm công được tạo tương đối so với ngày chạy lệnh, nên chạy lại để các cảnh báo "sắp hết hạn" luôn hợp lý).

Biến môi trường tuỳ chọn: `HR_SECRET_KEY` (khoá session; nếu không có sẽ tự sinh vào `instance/secret.key`), `HR_DATA_DIR`, `HR_BACKUP_DIR`, `HR_COOKIE_SECURE=1` (khi chạy HTTPS).

## Tài khoản demo
| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Manager | `manager` | `Manager@123` |
| Lecturer | `lecturer` | `Lecturer@123` (hồ sơ GV001 – Nguyễn Văn An) |

Mật khẩu được băm bằng Werkzeug trong `data/users.json`. Đổi mật khẩu demo trước khi triển khai thật.

## Phân quyền
| Chức năng | ADMIN | MANAGER | LECTURER |
|---|---|---|---|
| Giảng viên: xem / thêm / sửa | ✔ / ✔ / ✔ | ✔ / ✔ / ✔ | chỉ hồ sơ mình; sửa email, SĐT, địa chỉ, ảnh |
| Giảng viên: xoá | ✔ | ✘ | ✘ |
| Khoa | CRUD | chỉ xem | ✘ |
| Bộ môn | CRUD | CRUD | ✘ |
| Hợp đồng, Chấm công (ghi) | CRUD | chỉ xem | chỉ xem của mình (+ tự chấm công) |
| Nghỉ phép | gửi, duyệt, xoá | gửi, duyệt | gửi đơn, xem của mình |
| Đánh giá | CRUD | thêm/sửa | chỉ xem của mình |
| Tài khoản, Audit log, Backup/Restore, Import/Export, Cấu hình | ✔ | ✘ | ✘ |

## API (đều yêu cầu đăng nhập; ghi dữ liệu cần header `X-CSRF-Token`)
```
POST   /api/auth/login | /logout | /forgot | /change-password        GET /api/auth/me
GET|POST        /api/lecturers          GET|PUT|DELETE /api/lecturers/<id>
GET             /api/lecturers/<id>/profile      GET /api/lecturers/export.csv
GET|POST|PUT|DELETE  /api/faculties  /api/departments  /api/contracts  /api/attendance
                     /api/evaluations  /api/users            (…/<id> cho từng bản ghi)
GET|POST        /api/leave              DELETE /api/leave/<id>
POST            /api/leave/<id>/approve | /reject
POST            /api/attendance/check-in | /check-out
GET             /api/notifications      POST /api/notifications/<id>/read | /read-all   DELETE /api/notifications/<id>
GET             /api/audit-logs (Admin)           GET /api/search?q=
GET             /api/dashboard/stats | /campus | /me      GET /api/meta
GET|PUT         /api/system/settings    GET /api/system/info
GET|POST        /api/system/backups | /backup | /restore   DELETE /api/system/backups/<name>
GET             /api/system/export      POST /api/system/import
POST            /api/upload
```
Danh sách (GET) hỗ trợ `?page=&per_page=&q=&sort=&order=` và các bộ lọc theo field (vd `?faculty_id=CNTT&degree=Tiến sĩ`).

## Backup / Restore
- **Backup:** Cài đặt → *Sao lưu & khôi phục* → *Sao lưu dữ liệu*. Python copy toàn bộ `data/` vào `backup/YYYY-MM-DD_HH-MM-SS/`.
- **Restore:** bấm *Khôi phục* ở bản sao lưu mong muốn. Hệ thống tự tạo bản `…_truoc-khi-restore` trước khi ghi đè.
- **Export/Import JSON:** gộp mọi bảng vào 1 file; import kiểm tra tên bảng + kiểu dữ liệu và tự backup trước.
- Thủ công: chép thư mục `data/` ra nơi khác (hoặc chép ngược lại khi app đang tắt).

## Bảo mật đã áp dụng
Hash mật khẩu (Werkzeug), session cookie `HttpOnly` + `SameSite=Lax`, CSRF token cho mọi request ghi, phân quyền ở backend, giảng viên chỉ truy cập dữ liệu của mình, validate input phía server, escape HTML (Jinja autoescape + hàm `esc()` ở JS), chống path traversal khi restore, kiểm tra magic-bytes khi upload ảnh, khoá tạm đăng nhập sai, header `X-Content-Type-Options`/`X-Frame-Options`, SECRET_KEY ngoài source code.

**Giới hạn cần biết:** lưu JSON phù hợp quy mô nhỏ (đồ án/demo, vài nghìn bản ghi), không thay thế database cho hệ thống nhiều người dùng đồng thời. Khoá đăng nhập sai lưu trong RAM (mất khi restart). Chạy thật nên dùng HTTPS và WSGI server (gunicorn/waitress).

## Cấu trúc thư mục
```
university_hr/
├── app.py  config.py  requirements.txt  README.md
├── data/        # JSON database (users, lecturers, faculties, departments, contracts, attendance,
│                #   leave_requests, evaluations, notifications, audit_logs, system_settings)
├── backup/      # các bản sao lưu
├── services/    # data_manager, auth_service, lecturer_service, backup_service, notification_service
├── routes/      # auth.py, dashboard.py (các trang), api.py (REST)
├── templates/   # base, login, dashboard, lecturers, lecturer_detail, faculties, departments, contracts,
│                #   attendance, leave, evaluations, notifications, audit_logs, settings, 403/404/500
├── static/css/  # main, dashboard, login, responsive
├── static/js/   # main (tiện ích), crud (bảng dùng chung), pages (cấu hình từng trang), dashboard,
│                #   lecturers, notifications, charts, three-scene
├── utils/       # validators, decorators, helpers, seed_data
└── tests/       # test_api.py (python -m unittest tests.test_api -v)
```

## Kiểm thử
```bash
python -m unittest tests.test_api -v
```
Bộ test dùng thư mục dữ liệu tạm (không đụng `data/`), kiểm tra đăng nhập, CSRF, render mọi trang theo 3 vai trò, phân quyền API, validate, luồng nghỉ phép, chấm công, đánh giá, backup/restore/import.
"# university_hr" 
