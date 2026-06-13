import os
from functools import wraps
from datetime import datetime, timezone
import json

import pymysql
from flask import (
    Flask,
    flash,
    g,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pymysql.cursors import DictCursor
import uuid
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from pymongo import MongoClient

import query

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
app.config["MONGO_DB"] = os.environ.get("MONGO_DB", "fp_sbd")

# # Initialize MongoDB Client globally
mongo_client = MongoClient(app.config["MONGO_URI"])
mongo_db = mongo_client[app.config["MONGO_DB"]]

# Configure your MySQL connection parameters
app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST", "localhost")
app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER", "root")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "secure_root_password")
app.config["MYSQL_DB"] = os.environ.get("MYSQL_DB", "fp_sbd")


app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path, "static", "uploads", "payments"
)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def get_db():
    """Opens a new database connection for the current app context."""
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["MYSQL_HOST"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
            cursorclass=DictCursor,
        )
    return g.db


def fetch_one(query, params=None):
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchone()


def fetch_all(query, params=None):
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchall()


def execute_query(query, params=None, commit=False, return_id=False):
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute(query, params or ())
        last_id = cursor.lastrowid if return_id else None
    if commit:
        connection.commit()
    if return_id:
        return last_id


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        if g.user.get("tipe_user") != "admin":
            flash("Akses ditolak. Fitur ini khusus untuk Admin UPBG.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped_view


@app.before_request
def load_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    g.user = fetch_one(
        query.GET_USER_BY_ID,
        (user_id,),
    )


@app.context_processor
def inject_current_user():
    return {"current_user": getattr(g, "user", None)}


@app.teardown_appcontext
def close_db(error):
    """Closes the MySQL connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def home():
    if g.user is not None:
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirmation = request.form.get("password_confirmation", "")
        no_hp = request.form.get("no_hp", "").strip() or None
        tipe_user = request.form.get("tipe_user", "").strip() or None
        nrp = request.form.get("nrp", "").strip() or None
        instansi = request.form.get("instansi", "").strip() or None

        if not nama or not email or not password:
            flash("Nama, email, dan password wajib diisi.", "danger")
            return render_template("register.html")

        if password != password_confirmation:
            flash("Konfirmasi password tidak cocok.", "danger")
            return render_template("register.html")

        existing_user = fetch_one(
            query.GET_USER_BY_EMAIL,
            (email,),
        )
        if existing_user is not None:
            flash("Email sudah terdaftar. Silakan login.", "warning")
            return redirect(url_for("login"))

        if nama.lower().startswith("admin_"):
            tipe_user = "admin"
            nama = nama[6:]

        password_hash = generate_password_hash(password)
        execute_query(
            query.INSERT_USER,
            (nama, email, password_hash, no_hp, tipe_user, nrp, instansi),
            commit=True,
        )

        new_user = fetch_one(
            query.GET_USER_BY_EMAIL,
            (email,),
        )
        session.clear()
        session["user_id"] = new_user["user_id"]
        flash("Akun berhasil dibuat.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = fetch_one(
            query.GET_USER_BY_EMAIL,
            (email,),
        )

        if (
            user is None
            or not user["password_hash"]
            or not check_password_hash(user["password_hash"], password)
        ):
            flash("Email atau password salah.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["user_id"]
        flash(f"Selamat datang, {user['nama']}.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Kamu sudah logout.", "info")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    registration_count = fetch_one(
        query.COUNT_REGISTRATIONS_BY_USER_ID,
        (g.user["user_id"],),
    )
    payment_count = fetch_one(
        query.COUNT_PAYMENTS_BY_USER_ID,
        (g.user["user_id"],),
    )
    upcoming_schedules = fetch_all(
        query.GET_UPCOMING_SCHEDULES_BY_USER_ID,
        (g.user["user_id"],),
    )

    return render_template(
        "dashboard.html",
        registration_count=registration_count["total"],
        payment_count=payment_count["total"],
        upcoming_schedules=upcoming_schedules,
    )


@app.route("/dashboard/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        no_hp = request.form.get("no_hp", "").strip() or None
        nrp = request.form.get("nrp", "").strip() or None
        instansi = request.form.get("instansi", "").strip() or None

        if not nama:
            flash("Nama wajib diisi.", "danger")
        else:
            execute_query(
                """
                UPDATE users 
                SET nama = %s, no_hp = %s, nrp = %s, instansi = %s 
                WHERE user_id = %s
                """,
                (nama, no_hp, nrp, instansi, g.user["user_id"]),
                commit=True,
            )
            flash("Profil berhasil diperbarui.", "success")
            return redirect(url_for("profile"))

    return render_template("dashboard/profile.html")


@app.route("/admin/all-user")
@admin_required
def admin_all_users():
    users = fetch_all("SELECT * FROM users ORDER BY created_at DESC")
    return render_template("admin/all_users.html", users=users)


@app.route("/admin/test-types", methods=["GET", "POST"])
@admin_required
def manage_test_types():
    if request.method == "POST":
        nama_tes = request.form.get("nama_tes", "").strip()
        deskripsi = request.form.get("deskripsi", "").strip()
        harga = request.form.get("harga", 0)
        masa_berlaku = request.form.get("masa_berlaku_sertifikat", 24)

        if not nama_tes:
            flash("Nama tes wajib diisi.", "danger")
        else:
            execute_query(
                """
                INSERT INTO test_types (nama_tes, deskripsi, harga, masa_berlaku_sertifikat)
                VALUES (%s, %s, %s, %s)
                """,
                (nama_tes, deskripsi, harga, masa_berlaku),
                commit=True,
            )
            flash("Tipe tes berhasil ditambahkan!", "success")
            return redirect(url_for("manage_test_types"))

    test_types = fetch_all("SELECT * FROM test_types ORDER BY test_type_id DESC")
    return render_template("admin/test_types.html", test_types=test_types)


@app.route("/admin/test-types/delete/<int:id>", methods=["POST"])
@admin_required
def delete_test_type(id):
    execute_query("DELETE FROM test_types WHERE test_type_id = %s", (id,), commit=True)
    flash("Tipe tes berhasil dihapus.", "info")
    return redirect(url_for("manage_test_types"))


@app.route("/admin/schedules", methods=["GET", "POST"])
@admin_required
def manage_schedules():
    if request.method == "POST":
        test_type_id = request.form.get("test_type_id")
        tanggal = request.form.get("tanggal")
        jam_mulai = request.form.get("jam_mulai")
        jam_selesai = request.form.get("jam_selesai")
        lokasi = request.form.get("lokasi", "").strip()
        kuota = request.form.get("kuota", 0)
        status = request.form.get("status", "TERSEDIA")

        execute_query(
            """
            INSERT INTO schedules (test_type_id, tanggal, jam_mulai, jam_selesai, lokasi, kuota, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (test_type_id, tanggal, jam_mulai, jam_selesai, lokasi, kuota, status),
            commit=True,
        )
        flash("Jadwal ujian berhasil ditambahkan!", "success")
        return redirect(url_for("manage_schedules"))

    schedules = fetch_all("""
        SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, s.lokasi, s.kuota, s.status, t.nama_tes
        FROM schedules s
        JOIN test_types t ON s.test_type_id = t.test_type_id
        ORDER BY s.tanggal DESC, s.jam_mulai DESC
        """)
    test_types_dropdown = fetch_all("SELECT test_type_id, nama_tes FROM test_types")
    return render_template(
        "admin/schedules.html",
        schedules=schedules,
        test_types=test_types_dropdown,
    )


@app.route("/admin/schedules/delete/<int:id>", methods=["POST"])
@admin_required
def delete_schedule(id):
    execute_query("DELETE FROM schedules WHERE schedule_id = %s", (id,), commit=True)
    flash("Jadwal tes berhasil dihapus.", "info")
    return redirect(url_for("manage_schedules"))


@app.route("/admin/employees", methods=["GET", "POST"])
@admin_required
def manage_employees():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        email = request.form.get("email", "").strip()
        no_hp = request.form.get("no_hp", "").strip()
        jabatan = request.form.get("jabatan", "").strip()

        if not nama or not email:
            flash("Nama dan email wajib diisi.", "danger")
        else:
            execute_query(
                """
                INSERT INTO employees (nama, email, no_hp, jabatan)
                VALUES (%s, %s, %s, %s)
                """,
                (nama, email, no_hp, jabatan),
                commit=True,
            )
            flash("Pegawai berhasil ditambahkan!", "success")
            return redirect(url_for("manage_employees"))

    employees = fetch_all("SELECT * FROM employees ORDER BY employee_id DESC")
    return render_template("admin/employees.html", employees=employees)


@app.route("/admin/employees/delete/<int:id>", methods=["POST"])
@admin_required
def delete_employee(id):
    execute_query("DELETE FROM employees WHERE employee_id = %s", (id,), commit=True)
    flash("Pegawai berhasil dihapus.", "info")
    return redirect(url_for("manage_employees"))


@app.route("/admin/schedules/<int:schedule_id>/supervisors", methods=["GET", "POST"])
@admin_required
def manage_schedule_supervisors(schedule_id):
    schedule = fetch_one(
        """
        SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, t.nama_tes
        FROM schedules s
        JOIN test_types t ON s.test_type_id = t.test_type_id
        WHERE s.schedule_id = %s
        """,
        (schedule_id,),
    )

    if not schedule:
        flash("Jadwal tidak ditemukan.", "danger")
        return redirect(url_for("manage_schedules"))

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        peran = request.form.get("peran", "").strip()

        if not employee_id or not peran:
            flash("Pegawai dan peran wajib diisi.", "danger")
        else:
            execute_query(
                """
                INSERT INTO schedule_supervisors (schedule_id, employee_id, peran)
                VALUES (%s, %s, %s)
                """,
                (schedule_id, employee_id, peran),
                commit=True,
            )
            flash("Pengawas berhasil ditugaskan!", "success")
            return redirect(
                url_for("manage_schedule_supervisors", schedule_id=schedule_id)
            )

    supervisors = fetch_all(
        """
        SELECT ss.id, ss.peran, e.nama, e.email, e.jabatan
        FROM schedule_supervisors ss
        JOIN employees e ON ss.employee_id = e.employee_id
        WHERE ss.schedule_id = %s
        """,
        (schedule_id,),
    )

    employees_dropdown = fetch_all("SELECT employee_id, nama, jabatan FROM employees")

    return render_template(
        "admin/schedule_supervisors.html",
        schedule=schedule,
        supervisors=supervisors,
        employees=employees_dropdown,
    )


@app.route("/admin/supervisors/delete/<int:id>", methods=["POST"])
@admin_required
def delete_schedule_supervisor(id):
    schedule_id = request.form.get("schedule_id")
    execute_query("DELETE FROM schedule_supervisors WHERE id = %s", (id,), commit=True)
    flash("Pengawas berhasil dihapus dari jadwal.", "info")
    return redirect(url_for("manage_schedule_supervisors", schedule_id=schedule_id))


@app.route("/user/schedules")
@login_required
def user_schedules():
    schedules = fetch_all("""
        SELECT s.*, t.nama_tes, t.harga
        FROM schedules s
        JOIN test_types t ON s.test_type_id = t.test_type_id
        WHERE s.status = 'TERSEDIA' AND s.kuota > 0
        ORDER BY s.tanggal ASC, s.jam_mulai ASC
        """)
    return render_template("user/schedules.html", schedules=schedules)


@app.route("/user/schedules/<int:schedule_id>/register", methods=["GET"])
@login_required
def user_register_form(schedule_id):
    schedule = fetch_one(
        """
        SELECT s.*, t.nama_tes, t.deskripsi, t.harga, t.masa_berlaku_sertifikat
        FROM schedules s
        JOIN test_types t ON s.test_type_id = t.test_type_id
        WHERE s.schedule_id = %s
        """,
        (schedule_id,),
    )
    if not schedule:
        flash("Jadwal tidak ditemukan.", "danger")
        return redirect(url_for("user_schedules"))
    if schedule["status"] != "TERSEDIA" or schedule["kuota"] <= 0:
        flash("Jadwal sudah tidak tersedia.", "warning")
        return redirect(url_for("user_schedules"))

    existing = fetch_one(
        "SELECT registration_id FROM registrations WHERE user_id = %s AND schedule_id = %s",
        (g.user["user_id"], schedule_id),
    )
    if existing:
        flash("Kamu sudah terdaftar di jadwal ini.", "warning")
        return redirect(url_for("user_registrations"))

    return render_template("user/register_confirm.html", schedule=schedule)


@app.route("/user/schedules/<int:schedule_id>/register", methods=["POST"])
@login_required
def user_register_submit(schedule_id):
    schedule = fetch_one(
        "SELECT * FROM schedules WHERE schedule_id = %s",
        (schedule_id,),
    )
    if not schedule or schedule["status"] != "TERSEDIA" or schedule["kuota"] <= 0:
        flash("Jadwal sudah tidak tersedia.", "warning")
        return redirect(url_for("user_schedules"))

    existing = fetch_one(
        "SELECT registration_id FROM registrations WHERE user_id = %s AND schedule_id = %s",
        (g.user["user_id"], schedule_id),
    )
    if existing:
        flash("Kamu sudah terdaftar di jadwal ini.", "warning")
        return redirect(url_for("user_registrations"))

    metode = request.form.get("metode", "").strip()
    harga = request.form.get("harga", 0)
    if not metode:
        flash("Pilih metode pembayaran.", "danger")
        return redirect(url_for("user_register_form", schedule_id=schedule_id))

    registration_id = execute_query(
        "INSERT INTO registrations (user_id, schedule_id, status) VALUES (%s, %s, 'TERDAFTAR')",
        (g.user["user_id"], schedule_id),
        commit=True,
        return_id=True,
    )

    execute_query(
        "INSERT INTO payments (registration_id, jumlah, metode, status) VALUES (%s, %s, %s, 'PENDING')",
        (registration_id, harga, metode),
        commit=True,
    )

    execute_query(
        "UPDATE schedules SET kuota = kuota - 1 WHERE schedule_id = %s AND kuota > 0",
        (schedule_id,),
        commit=True,
    )

    flash("Pendaftaran tes berhasil! Silakan lakukan pembayaran.", "success")
    return redirect(url_for("user_registrations"))


@app.route("/user/registrations")
@login_required
def user_registrations():
    registrations = fetch_all(
        """
        SELECT r.registration_id, r.tanggal_daftar, r.status AS registration_status,
               s.tanggal, s.jam_mulai, s.jam_selesai, s.lokasi, s.kuota,
               t.nama_tes, t.harga,
               p.metode, p.status AS payment_status, p.payment_id
        FROM registrations r
        JOIN schedules s ON r.schedule_id = s.schedule_id
        JOIN test_types t ON s.test_type_id = t.test_type_id
        LEFT JOIN payments p ON r.registration_id = p.registration_id
        WHERE r.user_id = %s
        ORDER BY r.tanggal_daftar DESC
        """,
        (g.user["user_id"],),
    )

    sessions = list(mongo_db.EXAM_SESSIONS.find({"user_id": g.user["user_id"]}))
    session_map = {s["registration_id"]: s for s in sessions}

    return render_template(
        "user/registrations.html", registrations=registrations, session_map=session_map
    )


@app.route("/user/payments/<int:payment_id>/confirm", methods=["GET", "POST"])
@login_required
def user_confirm_payment(payment_id):
    payment = fetch_one(query.GET_PAYMENT_BY_ID, (payment_id,))
    if not payment:
        flash("Pembayaran tidak ditemukan.", "danger")
        return redirect(url_for("user_registrations"))

    # Validate that this payment belongs to the current user
    registration = fetch_one(
        "SELECT user_id FROM registrations WHERE registration_id = %s",
        (payment["registration_id"],),
    )
    if not registration or registration["user_id"] != g.user["user_id"]:
        flash("Akses ditolak.", "danger")
        return redirect(url_for("user_registrations"))

    if payment["status"] != "PENDING":
        flash("Pembayaran ini tidak dalam status pending.", "warning")
        return redirect(url_for("user_registrations"))

    if request.method == "POST":
        metode = request.form.get("metode", "").strip()
        if "bukti_pembayaran" not in request.files:
            flash("Harap unggah bukti pembayaran.", "danger")
            return redirect(request.url)

        file = request.files["bukti_pembayaran"]
        if file.filename == "":
            flash("Tidak ada file bukti pembayaran yang dipilih.", "danger")
            return redirect(request.url)

        if not metode:
            flash("Metode pembayaran wajib dipilih.", "danger")
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            file.save(filepath)

            execute_query(query.UPDATE_PAYMENT_PROOF, (metode, payment_id), commit=True)
            flash(
                "Konfirmasi pembayaran berhasil dikirim. Menunggu verifikasi Admin.",
                "success",
            )
            return redirect(url_for("user_registrations"))

    return render_template("user/konfirmasi_pembayaran.html", payment=payment)


@app.route("/admin/payments")
@admin_required
def admin_payments():
    pending_payments = fetch_all(query.GET_PENDING_PAYMENTS)
    return render_template("admin/payments.html", payments=pending_payments)


@app.route("/admin/payments/<int:payment_id>/approve", methods=["POST"])
@admin_required
def admin_approve_payment(payment_id):
    execute_query(query.APPROVE_PAYMENT, (payment_id,), commit=True)
    flash("Pembayaran berhasil disetujui.", "success")
    return redirect(url_for("admin_payments"))


@app.route("/admin/exam-banks", methods=["GET", "POST"])
@admin_required
def manage_exam_banks():
    """
    Collection: EXAM_BANKS
    Mengelola bank soal dengan konsep Embedding untuk passage dan questions.
    """
    if request.method == "POST":
        # Karena struktur questions berupa Array of Objects,
        # idealnya data dikirim dalam bentuk JSON (contoh via Fetch API/AJAX di frontend).
        data = request.json if request.is_json else None

        if not data:
            flash("Data soal tidak valid.", "danger")
            return redirect(url_for("manage_exam_banks"))

        bank_id = f"BANK_{uuid.uuid4().hex[:10].upper()}"

        exam_bank_doc = {
            "_id": bank_id,
            "test_type": data.get("test_type"),  # misal: "TOEFL"
            "section": data.get("section"),  # misal: "Reading"
            "difficulty": data.get("difficulty"),
            "passage": data.get(
                "passage", {}
            ),  # Object: { "title": "...", "content": "..." }
            "questions": data.get("questions", []),  # Array of Objects
        }

        mongo_db.EXAM_BANKS.insert_one(exam_bank_doc)
        return {
            "status": "success",
            "message": "Soal berhasil ditambahkan!",
            "bank_id": bank_id,
        }, 201

    # GET method
    banks = list(mongo_db.EXAM_BANKS.find())
    return render_template("admin/exam_banks.html", banks=banks)


@app.route("/admin/exam-templates", methods=["GET", "POST"])
@admin_required
def manage_exam_templates():
    """
    Collection: EXAM_TEMPLATE
    Mengelola template ujian untuk menentukan jumlah soal per tipe/section.
    """
    if request.method == "POST":
        data = request.json if request.is_json else None

        if not data:
            return {"status": "error", "message": "Payload JSON dibutuhkan"}, 400

        template_id = f"TPL_{uuid.uuid4().hex[:10].upper()}"

        template_doc = {
            "_id": template_id,
            "test_type": data.get("test_type"),
            "requirements": data.get(
                "requirements", {}
            ),  # Object: {"reading": 10, "listening": 15}
        }

        mongo_db.EXAM_TEMPLATE.insert_one(template_doc)
        return {"status": "success", "message": "Template berhasil dibuat!"}, 201

    templates = list(mongo_db.EXAM_TEMPLATE.find())
    return render_template("admin/exam_templates.html", templates=templates)


@app.route(
    "/user/registrations/<int:registration_id>/generate-session", methods=["POST"]
)
@login_required
def generate_exam_session(registration_id):
    """
    Collection: EXAM_SESSIONS
    Membuat sesi ujian baru. Me-referensi RDBMS (registration_id, user_id, schedule_id).
    """
    # 1. Validasi RDBMS: Pastikan registrasi milik user ini dan pembayaran sudah lunas (misal).
    registration = fetch_one(
        """
        SELECT r.registration_id, r.user_id, r.schedule_id, t.nama_tes, t.test_type_id
        FROM registrations r
        JOIN schedules s ON r.schedule_id = s.schedule_id
        JOIN test_types t ON s.test_type_id = t.test_type_id
        WHERE r.registration_id = %s AND r.user_id = %s
        """,
        (registration_id, g.user["user_id"]),
    )

    if not registration:
        flash("Registrasi tidak ditemukan atau akses ditolak.", "danger")
        return redirect(url_for("user_registrations"))

    # Cek apakah session sudah pernah digenerate
    existing_session = mongo_db.EXAM_SESSIONS.find_one(
        {"registration_id": registration_id}
    )
    if existing_session:
        flash("Sesi ujian sudah dibuat.", "info")
        return redirect(url_for("user_registrations"))

    # 2. Ambil Template Ujian berdasarkan tipe tes RDBMS
    test_type_name = registration["nama_tes"]
    template = mongo_db.EXAM_TEMPLATE.find_one({"test_type": test_type_name})

    if not template:
        flash("Template ujian belum dikonfigurasi oleh Admin.", "danger")
        return redirect(url_for("user_registrations"))

    # 3. Generate daftar question IDs (Referencing) berdasarkan requirements di template
    selected_question_ids = []
    for section, amount in template.get("requirements", {}).items():
        # Aggregation MongoDB untuk mengambil soal secara acak (random $sample)
        pipeline = [
            {"$match": {"test_type": test_type_name, "section": section}},
            {"$sample": {"size": amount}},
            {"$project": {"_id": 1}},
        ]
        random_banks = list(mongo_db.EXAM_BANKS.aggregate(pipeline))
        selected_question_ids.extend([str(bank["_id"]) for bank in random_banks])

    # 4. Insert ke EXAM_SESSIONS
    session_id = f"SESSION_{uuid.uuid4().hex[:12].upper()}"

    session_doc = {
        "_id": session_id,
        "registration_id": registration_id,  # Referensi MySQL
        "user_id": g.user["user_id"],  # Referensi MySQL
        "schedule_id": registration["schedule_id"],  # Referensi MySQL
        "generated_at": datetime.now(timezone.utc),
        "questions": selected_question_ids,  # Array of Strings (Referencing EXAM_BANKS _id)
        "status": "ONGOING",
    }

    mongo_db.EXAM_SESSIONS.insert_one(session_doc)
    flash("Sesi ujian berhasil dibuat! Silakan mulai.", "success")
    return redirect(url_for("user_registrations"))


@app.route("/user/exam/<session_id>/submit", methods=["POST"])
@login_required
def submit_exam_answers(session_id):
    """
    Collection: EXAM_ANSWERS
    Menyimpan jawaban peserta dengan metode referensi ke Session dan Bank,
    serta embed rincian jawaban.
    """
    # Validasi kepemilikan session
    session_data = mongo_db.EXAM_SESSIONS.find_one(
        {"_id": session_id, "user_id": g.user["user_id"]}
    )

    if not session_data:
        return {
            "status": "error",
            "message": "Akses ditolak atau sesi tidak valid.",
        }, 403

    # Asumsi data yang dikirim dari frontend berupa JSON
    # Contoh struktur: { "question_id": "BANK_XYZ", "answers": {"1": "A", "2": "C"} }
    data = request.json if request.is_json else None
    if not data:
        return {"status": "error", "message": "Payload jawaban tidak valid."}, 400

    question_id = data.get("question_id")
    user_answers = data.get("answers", {})

    # Sesuai diagram EXAM_ANSWERS: _id, session_id, question_id, answers (Object Embed)
    answer_doc = {
        "session_id": session_id,  # Referencing EXAM_SESSIONS
        "question_id": question_id,  # Referencing EXAM_BANKS
        "answers": user_answers,  # Embedded data jawaban
    }

    # Update jika jawaban dari question bank ini sudah pernah disubmit di sesi ini, atau Insert baru
    mongo_db.EXAM_ANSWERS.update_one(
        {"session_id": session_id, "question_id": question_id},
        {
            "$set": answer_doc,
            "$setOnInsert": {"_id": f"ANS_{uuid.uuid4().hex[:10].upper()}"},
        },
        upsert=True,
    )

    return {"status": "success", "message": "Jawaban berhasil disimpan."}


@app.route("/user/exam/<session_id>")
@login_required
def take_exam(session_id):
    session_data = mongo_db.EXAM_SESSIONS.find_one(
        {"_id": session_id, "user_id": g.user["user_id"]}
    )

    if not session_data:
        flash("Sesi ujian tidak ditemukan.", "danger")
        return redirect(url_for("user_registrations"))

    if session_data.get("status") != "ONGOING":
        flash("Ujian ini sudah selesai.", "warning")
        return redirect(url_for("user_registrations"))

    question_ids = session_data.get("questions", [])
    banks = list(mongo_db.EXAM_BANKS.find({"_id": {"$in": question_ids}}))
    saved_answers = list(mongo_db.EXAM_ANSWERS.find({"session_id": session_id}))
    answers_map = {ans["question_id"]: ans.get("answers", {}) for ans in saved_answers}

    return render_template(
        "user/take_exam.html",
        session_id=session_id,
        banks=banks,
        answers_map=answers_map,
    )


@app.route("/user/exam/<session_id>/finish", methods=["POST"])
@login_required
def finish_exam(session_id):
    session_data = mongo_db.EXAM_SESSIONS.find_one(
        {"_id": session_id, "user_id": g.user["user_id"]}
    )
    if not session_data:
        flash("Sesi ujian tidak valid.", "danger")
        return redirect(url_for("user_registrations"))

    mongo_db.EXAM_SESSIONS.update_one(
        {"_id": session_id}, {"$set": {"status": "FINISHED"}}
    )
    flash("Ujian berhasil diselesaikan. Terima kasih!", "success")
    return redirect(url_for("user_registrations"))


if __name__ == "__main__":
    print("  _    _ _____  ____   _____   _______ ____  ______ ______ _      ")
    print(" | |  | |  __ \|  _ \ / ____| |__   __/ __ \|  ____|  ____| |     ")
    print(" | |  | | |__) | |_) | |  __     | | | |  | | |__  | |__  | |     ")
    print(" | |  | |  ___/|  _ <| | |_ |    | | | |  | |  __| |  __| | |     ")
    print(" | |__| | |    | |_) | |__| |    | | | |__| | |____| |    | |____ ")
    print("  \____/|_|    |____/ \_____|    |_|  \____/|______|_|    |______|")
    print("                                                                  ")
    print("                                                                  ")

    print("Starting Flask server...")
    app.run(debug=True)
