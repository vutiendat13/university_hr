/* pages.js — cấu hình cho từng trang CRUD (cột, form, bộ lọc, quyền hiển thị nút).
   Quyền ở đây CHỈ để ẩn/hiện nút; backend luôn kiểm tra lại mọi request. */
const STAFF = ['ADMIN', 'MANAGER'], ADMIN = ['ADMIN'], EVERYONE = ['ADMIN', 'MANAGER', 'LECTURER'];
const person = (name, sub, p) => `<div class="cell-person">${p ? avatar(p, 'sm') : ''}<div><b>${esc(name)}</b><small>${esc(sub)}</small></div></div>`;
const academicYear = () => { const d = new Date(), y = d.getFullYear(); return d.getMonth() >= 7 ? `Năm học ${y}-${y + 1}` : `Năm học ${y - 1}-${y}`; };
const scoreBar = (v, max = 5) => `<div class="row" style="gap:8px;flex-wrap:nowrap"><div class="bar" style="width:90px"><i style="width:${(v / max) * 100}%"></i></div><b>${esc(v)}</b></div>`;

const Pages = {
  lecturerFields: M => [
    { name: 'id', label: 'Mã giảng viên', required: true, readonlyOnEdit: true, placeholder: 'VD: GV059', max: 12 },
    { name: 'full_name', label: 'Họ và tên', required: true, max: 80 },
    { name: 'dob', label: 'Ngày sinh', type: 'date', required: true }, { name: 'gender', label: 'Giới tính', type: 'select', options: M.genders, required: true },
    { name: 'cccd', label: 'CCCD', required: true, max: 12 }, { name: 'email', label: 'Email', type: 'email', required: true },
    { name: 'phone', label: 'Số điện thoại', type: 'tel', required: true, placeholder: '0912345678' }, { name: 'join_date', label: 'Ngày vào trường', type: 'date', required: true },
    { name: 'address', label: 'Địa chỉ', col: 12 },
    { name: 'faculty_id', label: 'Khoa', type: 'select', lookup: 'faculties', required: true },
    { name: 'department_id', label: 'Bộ môn', type: 'select', lookup: 'departments', dependsOn: 'faculty_id', required: true },
    { name: 'position', label: 'Chức vụ', type: 'select', options: M.positions, required: true }, { name: 'degree', label: 'Trình độ', type: 'select', options: M.degrees, required: true },
    { name: 'contract_type', label: 'Loại hợp đồng', type: 'select', options: M.lecturer_contract_types, required: true },
    { name: 'work_status', label: 'Tình trạng công tác', type: 'select', options: M.work_status, hideOnCreate: true },
    { name: 'avatar', label: 'Ảnh đại diện', type: 'avatar', col: 12 }
  ],
  defs: {
    lecturers: M => ({
      resource: 'lecturers', title: 'Quản lý giảng viên', subtitle: 'Hồ sơ cán bộ giảng dạy của trường', noun: 'giảng viên', addLabel: 'Thêm giảng viên',
      searchPlaceholder: 'Tìm theo tên, mã GV, email, trình độ…', nameOf: r => `${r.id} – ${r.full_name}`, viewUrl: r => `/lecturers/${r.id}`, sort: 'id',
      can: { create: STAFF, update: STAFF, delete: ADMIN },
      headActions: [{ label: 'Export CSV', icon: 'fa-file-csv', roles: STAFF, run: () => location.href = '/api/lecturers/export.csv' }],
      columns: [
        { key: 'avatar', label: 'Ảnh', detail: false, render: r => avatar(r, 'sm') }, { key: 'id', label: 'Mã GV', sort: true },
        { key: 'full_name', label: 'Họ tên', sort: true, render: r => `<a href="/lecturers/${esc(r.id)}"><b>${esc(r.full_name)}</b></a>` },
        { key: 'gender', label: 'Giới tính' }, { key: 'dob', label: 'Ngày sinh', render: r => fmtDate(r.dob) },
        { key: 'faculty_name', label: 'Khoa' }, { key: 'department_name', label: 'Bộ môn' }, { key: 'position', label: 'Chức vụ' },
        { key: 'degree', label: 'Trình độ', sort: true }, { key: 'email', label: 'Email' }, { key: 'phone', label: 'Số điện thoại' },
        { key: 'status', label: 'Trạng thái', render: r => badge(r.status) }
      ],
      fields: Pages.lecturerFields(M),
      filters: [
        { name: 'faculty_id', label: 'Khoa', lookup: 'faculties' }, { name: 'department_id', label: 'Bộ môn', lookup: 'departments' },
        { name: 'gender', label: 'Giới tính', options: M.genders }, { name: 'degree', label: 'Trình độ', options: M.degrees },
        { name: 'position', label: 'Chức vụ', options: M.positions }, { name: 'contract_type', label: 'Loại hợp đồng', options: M.lecturer_contract_types },
        { name: 'status', label: 'Trạng thái', options: ['Đang làm việc', 'Đang nghỉ phép', 'Đã nghỉ việc'] }
      ]
    }),

    faculties: M => ({
      resource: 'faculties', title: 'Quản lý khoa', subtitle: 'Danh sách khoa, trưởng khoa và quy mô giảng viên', noun: 'khoa', addLabel: 'Thêm khoa', nameOf: r => r.name,
      can: { create: ADMIN, update: ADMIN, delete: ADMIN }, sort: 'id',
      columns: [{ key: 'id', label: 'Mã khoa', sort: true }, { key: 'name', label: 'Tên khoa', sort: true, render: r => `<b>${esc(r.name)}</b>` }, { key: 'dean', label: 'Trưởng khoa' },
        { key: 'department_count', label: 'Số bộ môn' }, { key: 'lecturer_count', label: 'Số giảng viên', sort: true }, { key: 'status', label: 'Trạng thái', render: r => badge(r.status) }],
      fields: [{ name: 'id', label: 'Mã khoa', required: true, readonlyOnEdit: true, placeholder: 'VD: CNTT', max: 10 }, { name: 'name', label: 'Tên khoa', required: true },
        { name: 'dean', label: 'Trưởng khoa' }, { name: 'status', label: 'Trạng thái', type: 'select', options: M.faculty_status, required: true, default: 'Hoạt động' },
        { name: 'description', label: 'Mô tả', type: 'textarea', col: 12 }],
      filters: [{ name: 'status', label: 'Trạng thái', options: M.faculty_status }],
      actions: [{
        key: 'tree', icon: 'fa-sitemap', title: 'Xem bộ môn', run: async r => {
          const d = await api('GET', `/api/departments?faculty_id=${encodeURIComponent(r.id)}&per_page=100`);
          Modal.info(r.name, d.items.length ? `<ul class="timeline">${d.items.map(x => `<li><b>${esc(x.name)}</b><br><small class="muted">Trưởng bộ môn: ${esc(x.head || '—')} · ${x.lecturer_count} giảng viên</small></li>`).join('')}</ul>` : '<div class="empty">Khoa chưa có bộ môn.</div>');
        }
      }, {
        key: 'members', icon: 'fa-users', title: 'Giảng viên của khoa', roles: STAFF, run: r => Pages.showMembers(`Giảng viên – ${r.name}`, { faculty_id: r.id })
      }]
    }),

    departments: M => ({
      resource: 'departments', title: 'Quản lý bộ môn', subtitle: 'Mỗi khoa gồm nhiều bộ môn', noun: 'bộ môn', addLabel: 'Thêm bộ môn', nameOf: r => r.name,
      can: { create: STAFF, update: STAFF, delete: STAFF }, sort: 'faculty_id',
      columns: [{ key: 'id', label: 'Mã', sort: true }, { key: 'name', label: 'Tên bộ môn', sort: true, render: r => `<b>${esc(r.name)}</b>` }, { key: 'faculty_name', label: 'Khoa' },
        { key: 'head', label: 'Trưởng bộ môn' }, { key: 'lecturer_count', label: 'Số giảng viên', sort: true }],
      fields: [{ name: 'name', label: 'Tên bộ môn', required: true }, { name: 'faculty_id', label: 'Khoa', type: 'select', lookup: 'faculties', required: true },
        { name: 'head', label: 'Trưởng bộ môn' }, { name: 'id', label: 'Mã bộ môn (tuỳ chọn)', readonlyOnEdit: true, placeholder: 'Để trống để tự sinh', max: 12 }],
      filters: [{ name: 'faculty_id', label: 'Khoa', lookup: 'faculties' }],
      actions: [{ key: 'members', icon: 'fa-users', title: 'Giảng viên thuộc bộ môn', roles: STAFF, run: r => Pages.showMembers(`Giảng viên – ${r.name}`, { department_id: r.id }) }]
    }),

    contracts: M => ({
      resource: 'contracts', title: 'Quản lý hợp đồng', subtitle: 'Hợp đồng làm việc; hệ thống tự cảnh báo khi sắp hết hạn', noun: 'hợp đồng', addLabel: 'Thêm hợp đồng',
      nameOf: r => `${r.id} – ${r.lecturer_name}`, can: { create: ADMIN, update: ADMIN, delete: ADMIN }, sort: 'id', order: 'desc',
      columns: [{ key: 'id', label: 'Mã HĐ', sort: true }, { key: 'lecturer_name', label: 'Giảng viên', render: r => person(r.lecturer_name, r.lecturer_id) }, { key: 'type', label: 'Loại hợp đồng' },
        { key: 'start_date', label: 'Bắt đầu', render: r => fmtDate(r.start_date) },
        { key: 'end_date', label: 'Kết thúc', sort: true, render: r => r.end_date ? `${fmtDate(r.end_date)}${r.days_left !== null && r.days_left >= 0 && r.status === 'Sắp hết hạn' ? ` <small class="muted">(còn ${r.days_left} ngày)</small>` : ''}` : 'Không thời hạn' },
        { key: 'status', label: 'Trạng thái', render: r => badge(r.status) }, { key: 'note', label: 'Ghi chú', wrap: true }],
      fields: [{ name: 'lecturer_id', label: 'Giảng viên', type: 'select', lookup: 'lecturers', required: true, readonlyOnEdit: true, col: 12 },
        { name: 'type', label: 'Loại hợp đồng', type: 'select', options: M.contract_kinds, required: true },
        { name: 'start_date', label: 'Ngày bắt đầu', type: 'date', required: true }, { name: 'end_date', label: 'Ngày kết thúc', type: 'date' },
        { name: 'note', label: 'Ghi chú', col: 12 }],
      filters: [{ name: 'faculty_id', label: 'Khoa', lookup: 'faculties' }, { name: 'type', label: 'Loại hợp đồng', options: M.contract_kinds }, { name: 'status', label: 'Trạng thái', options: ['Đang hiệu lực', 'Sắp hết hạn', 'Đã hết hạn'] }],
      banner: async page => {
        const d = await api('GET', '/api/contracts?status=' + encodeURIComponent('Sắp hết hạn') + '&per_page=1');
        return d.total ? `<div class="banner"><i class="fa-solid fa-triangle-exclamation"></i> Có ${d.total} hợp đồng sắp hết hạn cần xử lý.<button class="btn sm ghost" onclick="Pages.filterContracts()">Chỉ xem các hợp đồng này</button></div>` : '';
      }
    }),

    attendance: M => ({
      resource: 'attendance', title: 'Chấm công', subtitle: 'Theo dõi giờ vào – giờ ra của giảng viên', noun: 'bản ghi chấm công', addLabel: 'Thêm bản ghi',
      nameOf: r => `${r.lecturer_name} ngày ${fmtDate(r.date)}`, can: { create: ADMIN, update: ADMIN, delete: ADMIN }, sort: 'date', order: 'desc',
      headActions: [
        { label: 'Chấm công vào', icon: 'fa-right-to-bracket', cls: 'primary', roles: ['LECTURER'], run: p => api('POST', '/api/attendance/check-in').then(() => { toast('Chấm công vào thành công'); p.load(); }).catch(e => toast(e.message, 'error')) },
        { label: 'Chấm công ra', icon: 'fa-right-from-bracket', roles: ['LECTURER'], run: p => api('POST', '/api/attendance/check-out').then(() => { toast('Chấm công ra thành công'); p.load(); }).catch(e => toast(e.message, 'error')) }],
      columns: [{ key: 'lecturer_name', label: 'Giảng viên', render: r => person(r.lecturer_name, `${r.lecturer_id} · ${r.faculty_name}`) }, { key: 'date', label: 'Ngày', sort: true, render: r => fmtDate(r.date) },
        { key: 'check_in', label: 'Giờ vào', render: r => esc(r.check_in || '—') }, { key: 'check_out', label: 'Giờ ra', render: r => esc(r.check_out || '—') },
        { key: 'status', label: 'Trạng thái', render: r => badge(r.status) }, { key: 'note', label: 'Ghi chú', wrap: true }],
      fields: [{ name: 'lecturer_id', label: 'Giảng viên', type: 'select', lookup: 'lecturers', required: true, readonlyOnEdit: true, col: 12 }, { name: 'date', label: 'Ngày', type: 'date', required: true },
        { name: 'status', label: 'Trạng thái', type: 'select', options: M.attendance_status, required: true }, { name: 'check_in', label: 'Giờ vào', type: 'time' }, { name: 'check_out', label: 'Giờ ra', type: 'time' },
        { name: 'note', label: 'Ghi chú', col: 12 }],
      filters: [{ name: 'date', label: 'Ngày', type: 'date' }, { name: 'month', label: 'Tháng', type: 'month' },
        { name: 'faculty_id', label: 'Khoa', lookup: 'faculties', roles: STAFF }, { name: 'lecturer_id', label: 'Giảng viên', lookup: 'lecturers', roles: STAFF },
        { name: 'status', label: 'Trạng thái', options: M.attendance_status }]
    }),

    leave: M => ({
      resource: 'leave', title: 'Nghỉ phép', subtitle: APP.user.role === 'LECTURER' ? 'Gửi và theo dõi đơn nghỉ phép của bạn' : 'Duyệt đơn nghỉ phép của giảng viên', noun: 'đơn nghỉ phép', addLabel: 'Gửi đơn nghỉ phép',
      nameOf: r => `${r.id} – ${r.lecturer_name}`, can: { create: EVERYONE, delete: ADMIN }, sort: 'created_at', order: 'desc', formSize: 'md',
      columns: [{ key: 'id', label: 'Mã đơn', sort: true }, { key: 'lecturer_name', label: 'Giảng viên', render: r => person(r.lecturer_name, `${r.lecturer_id} · ${r.faculty_name}`) },
        { key: 'type', label: 'Loại nghỉ' }, { key: 'from_date', label: 'Từ ngày', sort: true, render: r => fmtDate(r.from_date) }, { key: 'to_date', label: 'Đến ngày', render: r => fmtDate(r.to_date) },
        { key: 'reason', label: 'Lý do', wrap: true }, { key: 'status', label: 'Trạng thái', render: r => badge(r.status) }],
      fields: [{ name: 'lecturer_id', label: 'Giảng viên', type: 'select', lookup: 'lecturers', required: true, roles: STAFF, col: 12 }, { name: 'type', label: 'Loại nghỉ', type: 'select', options: M.leave_types, required: true, col: 12 },
        { name: 'from_date', label: 'Từ ngày', type: 'date', required: true }, { name: 'to_date', label: 'Đến ngày', type: 'date', required: true },
        { name: 'reason', label: 'Lý do', type: 'textarea', required: true, col: 12 }],
      filters: [{ name: 'status', label: 'Trạng thái', options: M.leave_status }, { name: 'type', label: 'Loại nghỉ', options: M.leave_types }, { name: 'faculty_id', label: 'Khoa', lookup: 'faculties', roles: STAFF }],
      actions: [
        { key: 'approve', icon: 'fa-check', title: 'Duyệt', cls: 'ok', roles: STAFF, show: r => r.status === 'Chờ duyệt', run: (r, p) => Pages.decide(r, 'approve', p) },
        { key: 'reject', icon: 'fa-xmark', title: 'Từ chối', cls: 'bad', roles: STAFF, show: r => r.status === 'Chờ duyệt', run: (r, p) => Pages.decide(r, 'reject', p) }],
      detail: r => `<h4 style="margin:20px 0 10px">Lịch sử xử lý</h4>${r.history?.length ? `<ul class="timeline">${r.history.map(h => `<li><b>${esc(h.action)}</b> bởi ${esc(h.by)} <small class="muted">· ${fmtDT(h.at)}</small>${h.note ? `<br><small>${esc(h.note)}</small>` : ''}</li>`).join('')}</ul>` : '<p class="muted">Chưa có xử lý nào.</p>'}`
    }),

    evaluations: M => ({
      resource: 'evaluations', title: 'Đánh giá giảng viên', subtitle: 'Chấm điểm 1–5 theo 6 tiêu chí; hệ thống tự tính điểm trung bình và xếp loại', noun: 'đánh giá', addLabel: 'Thêm đánh giá',
      nameOf: r => `${r.lecturer_name} – ${r.period}`, can: { create: STAFF, update: STAFF, delete: ADMIN }, sort: 'created_at', order: 'desc',
      columns: [{ key: 'lecturer_name', label: 'Giảng viên', render: r => person(r.lecturer_name, `${r.lecturer_id} · ${r.faculty_name}`) }, { key: 'period', label: 'Kỳ đánh giá', sort: true },
        { key: 'avg', label: 'Điểm TB', sort: true, render: r => scoreBar(r.avg) }, { key: 'grade', label: 'Xếp loại', render: r => badge(r.grade) },
        { key: 'evaluator', label: 'Người đánh giá' }, { key: 'created_at', label: 'Ngày', render: r => fmtDate(r.created_at) }],
      fields: [{ name: 'lecturer_id', label: 'Giảng viên', type: 'select', lookup: 'lecturers', required: true, readonlyOnEdit: true }, { name: 'period', label: 'Kỳ đánh giá', required: true, default: academicYear() },
        ...Object.entries(M.criteria).map(([k, l]) => ({ name: k, label: `${l} (1–5)`, type: 'select', options: [1, 2, 3, 4, 5], required: true, col: 4 })),
        { name: 'comment', label: 'Nhận xét', type: 'textarea', col: 12 }],
      filters: [{ name: 'grade', label: 'Xếp loại', options: M.grades }, { name: 'faculty_id', label: 'Khoa', lookup: 'faculties', roles: STAFF }],
      detail: r => `<h4 style="margin:20px 0 10px">Điểm theo tiêu chí</h4><div class="stack" style="gap:10px">${Object.entries(M.criteria).map(([k, l]) => `<div class="row" style="justify-content:space-between"><span>${esc(l)}</span>${scoreBar(r[k])}</div>`).join('')}</div>${r.comment ? `<h4 style="margin:20px 0 6px">Nhận xét</h4><p style="margin:0">${esc(r.comment)}</p>` : ''}`
    }),

    'audit-logs': M => ({
      resource: 'audit-logs', title: 'Nhật ký hệ thống', subtitle: 'Mọi thao tác quan trọng đều được ghi lại', noun: 'nhật ký', viewable: false, perPage: 15, sort: 'timestamp', order: 'desc',
      searchPlaceholder: 'Tìm theo người dùng, thao tác, đối tượng…',
      columns: [{ key: 'timestamp', label: 'Thời gian', sort: true, render: r => fmtDT(r.timestamp) }, { key: 'user', label: 'Người dùng', render: r => `<b>${esc(r.user)}</b>` }, { key: 'role', label: 'Vai trò', render: r => r.role ? badge(r.role) : '—' },
        { key: 'action', label: 'Thao tác' }, { key: 'target', label: 'Đối tượng' }, { key: 'ip', label: 'IP' }],
      filters: [{ name: 'role', label: 'Vai trò', options: M.roles }]
    }),

    users: M => ({
      resource: 'users', embedded: true, title: 'Quản lý tài khoản', noun: 'tài khoản', addLabel: 'Thêm tài khoản', nameOf: r => r.username, viewable: false, perPage: 8,
      can: { create: ADMIN, update: ADMIN, delete: ADMIN }, searchPlaceholder: 'Tìm tài khoản…',
      columns: [{ key: 'username', label: 'Tên đăng nhập', render: r => `<b>${esc(r.username)}</b>` }, { key: 'full_name', label: 'Họ tên' }, { key: 'role', label: 'Vai trò', render: r => badge(r.role) },
        { key: 'lecturer_name', label: 'Hồ sơ giảng viên', render: r => esc(r.lecturer_name || '—') }, { key: 'active', label: 'Trạng thái', render: r => badge(r.active === false ? 'Đã nghỉ việc' : 'Hoạt động').replace('Đã nghỉ việc', 'Đã khoá') }],
      fields: [{ name: 'username', label: 'Tên đăng nhập', required: true, readonlyOnEdit: true, max: 30 }, { name: 'full_name', label: 'Họ tên', required: true },
        { name: 'role', label: 'Vai trò', type: 'select', options: M.roles, required: true }, { name: 'email', label: 'Email', type: 'email' },
        { name: 'lecturer_id', label: 'Gắn với giảng viên (nếu là LECTURER)', type: 'select', lookup: 'lecturers', col: 12 },
        { name: 'password', label: 'Mật khẩu', type: 'password', required: true, hintEdit: 'Để trống nếu không muốn đổi mật khẩu', col: 12 },
        { name: 'active', label: '', type: 'checkbox', hint: 'Cho phép đăng nhập', col: 12 }],
      filters: [{ name: 'role', label: 'Vai trò', options: M.roles }]
    })
  },

  async mount(name, root = '#crud-root') {
    const M = await Meta.load(); const cfg = Pages.defs[name](M); cfg.root = root;
    return (Pages.current = new CrudPage(cfg));
  },
  async showMembers(title, params) {
    const d = await api('GET', `/api/lecturers?${new URLSearchParams({ per_page: 200, ...params })}`);
    Modal.info(title, d.items.length ? d.items.map(l => `<a class="li" style="text-decoration:none;color:inherit" href="/lecturers/${esc(l.id)}">${avatar(l, 'sm')}<div class="grow"><b>${esc(l.full_name)}</b><small>${esc(l.id)} · ${esc(l.position)}</small></div>${badge(l.degree)}</a>`).join('') : '<div class="empty">Chưa có giảng viên.</div>');
  },
  async decide(r, action, page) {
    const approve = action === 'approve';
    const note = await Modal.prompt({ title: `${approve ? 'Duyệt' : 'Từ chối'} đơn ${r.id}`, label: 'Ghi chú (không bắt buộc)', placeholder: approve ? 'VD: Đồng ý' : 'Lý do từ chối', confirm: approve ? 'Duyệt đơn' : 'Từ chối đơn', cls: approve ? 'ok' : 'danger' });
    if (note === null) return;
    try { await api('POST', `/api/leave/${r.id}/${action}`, { note }); toast(approve ? 'Đã duyệt đơn nghỉ phép' : 'Đã từ chối đơn nghỉ phép'); page.load(); page.afterDecide && page.afterDecide(); }
    catch (e) { toast(e.message, 'error'); }
  },
  filterContracts() {
    const p = Pages.current; p.st.filters = { status: 'Sắp hết hạn' }; p.st.page = 1;
    const s = $('select[name=status]', p.$filters); if (s) s.value = 'Sắp hết hạn'; p.load();
  }
};
