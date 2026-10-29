"""Điểm khởi chạy ứng dụng Flask: đăng ký blueprint, bảo vệ CSRF, header bảo mật, xử lý lỗi."""
import secrets

from flask import Flask, jsonify, render_template, request, session

import config as C
from config import Config
from routes import api, auth, dashboard
from services import lecturer_service as ls
from services import notification_service as ns
from services.auth_service import current_user, public_user
from utils.seed_data import seed


def create_app():
    gunicorn app:app
    app.config.from_object(Config)
    app.json.ensure_ascii = False
    if seed():  # lần chạy đầu: tự tạo dữ liệu demo
        print("Đã tạo dữ liệu demo trong thư mục data/")
    ns.check_contracts(int(ls.get_settings()["contract_warning_days"]))

    for bp in (auth.bp, dashboard.bp, api.bp):
        app.register_blueprint(bp)

    @app.before_request
    def csrf_protect():
        """Mọi request ghi dữ liệu phải gửi header X-CSRF-Token khớp với token trong session."""
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        if request.method in ("POST", "PUT", "DELETE", "PATCH") and request.path.startswith("/api/"):
            sent = request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(sent, session["csrf"]):
                return jsonify(message="Phiên làm việc không hợp lệ, vui lòng tải lại trang"), 400

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if not request.path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def inject_globals():
        user = current_user()
        nav = [n for n in C.NAV if user and user["role"] in n["roles"]]
        return {"user": public_user(user), "nav": nav, "csrf": session.get("csrf", ""), "sys": ls.get_settings()}

    def error_page(code, template, message):
        if request.path.startswith("/api/"):
            return jsonify(message=message), code
        return render_template(template), code

    app.register_error_handler(403, lambda e: error_page(403, "403.html", "Bạn không có quyền truy cập chức năng này"))
    app.register_error_handler(404, lambda e: error_page(404, "404.html", "Không tìm thấy tài nguyên"))
    app.register_error_handler(405, lambda e: error_page(405, "404.html", "Phương thức không được hỗ trợ"))
    app.register_error_handler(413, lambda e: error_page(413, "500.html", "Tệp quá lớn"))
    app.register_error_handler(500, lambda e: error_page(500, "500.html", "Lỗi hệ thống, vui lòng thử lại"))
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
