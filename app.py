import os
from functools import wraps

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
from werkzeug.security import check_password_hash, generate_password_hash

import query

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configure your MySQL connection parameters
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'secure_root_password')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'fp_sbd')

def get_db():
    """Opens a new database connection for the current app context."""
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            cursorclass=DictCursor
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


def execute_query(query, params=None, commit=False):
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute(query, params or ())
    if commit:
        connection.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        if g.user.get('tipe_user') != 'admin':
            flash('Akses ditolak. Fitur ini khusus untuk Admin UPBG.', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)

    return wrapped_view


@app.before_request
def load_current_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        return

    g.user = fetch_one(
        query.GET_USER_BY_ID,
        (user_id,),
    )


@app.context_processor
def inject_current_user():
    return {'current_user': getattr(g, 'user', None)}

@app.teardown_appcontext
def close_db(error):
    """Closes the MySQL connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Reads schema.sql and initializes the database tables."""
    print("Checking database tables...")
    # Open a direct connection outside of the request context
    connection = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    
    try:
        with connection.cursor(DictCursor) as cursor:
            # Read the raw SQL file
            with open('schema.sql', 'r') as f:
                sql_script = f.read()
            
            # Split the script into individual queries by semicolon
            sql_commands = sql_script.split(';')
            
            for command in sql_commands:
                # Execute only if the command is not an empty string
                if command.strip():
                    cursor.execute(command)

            cursor.execute(
                """
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'users'
                  AND column_name = 'password_hash'
                """,
                (app.config['MYSQL_DB'],),
            )
            column_count = cursor.fetchone()['column_count']
            if column_count == 0:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT '' AFTER email"
                )
                    
        connection.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        connection.close()

@app.route('/')
def home():
    if g.user is not None:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user is not None:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirmation = request.form.get('password_confirmation', '')
        no_hp = request.form.get('no_hp', '').strip() or None
        tipe_user = request.form.get('tipe_user', '').strip() or None
        nrp = request.form.get('nrp', '').strip() or None
        instansi = request.form.get('instansi', '').strip() or None

        if not nama or not email or not password:
            flash('Nama, email, dan password wajib diisi.', 'danger')
            return render_template('register.html')

        if password != password_confirmation:
            flash('Konfirmasi password tidak cocok.', 'danger')
            return render_template('register.html')
        
        existing_user = fetch_one(
            query.GET_USER_BY_EMAIL,
            (email,),
        )
        if existing_user is not None:
            flash('Email sudah terdaftar. Silakan login.', 'warning')
            return redirect(url_for('login'))

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
        session['user_id'] = new_user['user_id']
        flash('Akun berhasil dibuat.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = fetch_one(
            query.GET_USER_BY_EMAIL,
            (email,),
        )

        if user is None or not user['password_hash'] or not check_password_hash(user['password_hash'], password):
            flash('Email atau password salah.', 'danger')
            return render_template('login.html')

        session.clear()
        session['user_id'] = user['user_id']
        flash(f"Selamat datang, {user['nama']}.", 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Kamu sudah logout.', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    registration_count = fetch_one(
        query.COUNT_REGISTRATIONS_BY_USER_ID,
        (g.user['user_id'],),
    )
    payment_count = fetch_one(
        query.COUNT_PAYMENTS_BY_USER_ID,
        (g.user['user_id'],),
    )
    upcoming_schedules = fetch_all(
        query.GET_UPCOMING_SCHEDULES_BY_USER_ID,
        (g.user['user_id'],),
    )

    return render_template(
        'dashboard.html',
        registration_count=registration_count['total'],
        payment_count=payment_count['total'],
        upcoming_schedules=upcoming_schedules,
    )

@app.route('/admin/test-types', methods=['GET', 'POST'])
@admin_required
def manage_test_types():
    if request.method == 'POST':
        nama_tes = request.form.get('nama_tes', '').strip()
        deskripsi = request.form.get('deskripsi', '').strip()
        harga = request.form.get('harga', 0)
        masa_berlaku = request.form.get('masa_berlaku_sertifikat', 24)

        if not nama_tes:
            flash('Nama tes wajib diisi.', 'danger')
        else:
            execute_query(
                """
                INSERT INTO test_types (nama_tes, deskripsi, harga, masa_berlaku_sertifikat)
                VALUES (%s, %s, %s, %s)
                """,
                (nama_tes, deskripsi, harga, masa_berlaku),
                commit=True,
            )
            flash('Tipe tes berhasil ditambahkan!', 'success')
            return redirect(url_for('manage_test_types'))

    test_types = fetch_all(
        "SELECT * FROM test_types ORDER BY test_type_id DESC"
    )
    return render_template('admin/test_types.html', test_types=test_types)


@app.route('/admin/test-types/delete/<int:id>', methods=['POST'])
@admin_required
def delete_test_type(id):
    execute_query(
        "DELETE FROM test_types WHERE test_type_id = %s", (id,), commit=True
    )
    flash('Tipe tes berhasil dihapus.', 'info')
    return redirect(url_for('manage_test_types'))


@app.route('/admin/schedules', methods=['GET', 'POST'])
@admin_required
def manage_schedules():
    if request.method == 'POST':
        test_type_id = request.form.get('test_type_id')
        tanggal = request.form.get('tanggal')
        jam_mulai = request.form.get('jam_mulai')
        jam_selesai = request.form.get('jam_selesai')
        lokasi = request.form.get('lokasi', '').strip()
        kuota = request.form.get('kuota', 0)
        status = request.form.get('status', 'TERSEDIA')

        execute_query(
            """
            INSERT INTO schedules (test_type_id, tanggal, jam_mulai, jam_selesai, lokasi, kuota, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (test_type_id, tanggal, jam_mulai, jam_selesai, lokasi, kuota, status),
            commit=True,
        )
        flash('Jadwal ujian berhasil ditambahkan!', 'success')
        return redirect(url_for('manage_schedules'))

    schedules = fetch_all(
        """
        SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, s.lokasi, s.kuota, s.status, t.nama_tes
        FROM schedules s
        JOIN test_types t ON s.test_type_id = t.test_type_id
        ORDER BY s.tanggal DESC, s.jam_mulai DESC
        """
    )
    test_types_dropdown = fetch_all(
        "SELECT test_type_id, nama_tes FROM test_types"
    )
    return render_template(
        'admin/schedules.html',
        schedules=schedules,
        test_types=test_types_dropdown,
    )


@app.route('/admin/schedules/delete/<int:id>', methods=['POST'])
@admin_required
def delete_schedule(id):
    execute_query(
        "DELETE FROM schedules WHERE schedule_id = %s", (id,), commit=True
    )
    flash('Jadwal tes berhasil dihapus.', 'info')
    return redirect(url_for('manage_schedules'))


@app.route('/admin/employees', methods=['GET', 'POST'])
@admin_required
def manage_employees():
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        email = request.form.get('email', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        jabatan = request.form.get('jabatan', '').strip()

        if not nama or not email:
            flash('Nama dan email wajib diisi.', 'danger')
        else:
            execute_query(
                """
                INSERT INTO employees (nama, email, no_hp, jabatan)
                VALUES (%s, %s, %s, %s)
                """,
                (nama, email, no_hp, jabatan),
                commit=True,
            )
            flash('Pegawai berhasil ditambahkan!', 'success')
            return redirect(url_for('manage_employees'))

    employees = fetch_all("SELECT * FROM employees ORDER BY employee_id DESC")
    return render_template('admin/employees.html', employees=employees)


@app.route('/admin/employees/delete/<int:id>', methods=['POST'])
@admin_required
def delete_employee(id):
    execute_query("DELETE FROM employees WHERE employee_id = %s", (id,), commit=True)
    flash('Pegawai berhasil dihapus.', 'info')
    return redirect(url_for('manage_employees'))


@app.route('/admin/schedules/<int:schedule_id>/supervisors', methods=['GET', 'POST'])
@admin_required
def manage_schedule_supervisors(schedule_id):
    schedule = fetch_one(
        """
        SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, t.nama_tes
        FROM schedules s
        JOIN test_types t ON s.test_type_id = t.test_type_id
        WHERE s.schedule_id = %s
        """,
        (schedule_id,)
    )
    
    if not schedule:
        flash('Jadwal tidak ditemukan.', 'danger')
        return redirect(url_for('manage_schedules'))

    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        peran = request.form.get('peran', '').strip()

        if not employee_id or not peran:
            flash('Pegawai dan peran wajib diisi.', 'danger')
        else:
            execute_query(
                """
                INSERT INTO schedule_supervisors (schedule_id, employee_id, peran)
                VALUES (%s, %s, %s)
                """,
                (schedule_id, employee_id, peran),
                commit=True,
            )
            flash('Pengawas berhasil ditugaskan!', 'success')
            return redirect(url_for('manage_schedule_supervisors', schedule_id=schedule_id))

    supervisors = fetch_all(
        """
        SELECT ss.id, ss.peran, e.nama, e.email, e.jabatan
        FROM schedule_supervisors ss
        JOIN employees e ON ss.employee_id = e.employee_id
        WHERE ss.schedule_id = %s
        """,
        (schedule_id,)
    )
    
    employees_dropdown = fetch_all("SELECT employee_id, nama, jabatan FROM employees")
    
    return render_template(
        'admin/schedule_supervisors.html',
        schedule=schedule,
        supervisors=supervisors,
        employees=employees_dropdown
    )

@app.route('/admin/supervisors/delete/<int:id>', methods=['POST'])
@admin_required
def delete_schedule_supervisor(id):
    schedule_id = request.form.get('schedule_id')
    execute_query("DELETE FROM schedule_supervisors WHERE id = %s", (id,), commit=True)
    flash('Pengawas berhasil dihapus dari jadwal.', 'info')
    return redirect(url_for('manage_schedule_supervisors', schedule_id=schedule_id))


if __name__ == '__main__':
    print("  _    _ _____  ____   _____   _______ ____  ______ ______ _      ")
    print(" | |  | |  __ \|  _ \ / ____| |__   __/ __ \|  ____|  ____| |     ")
    print(" | |  | | |__) | |_) | |  __     | | | |  | | |__  | |__  | |     ")
    print(" | |  | |  ___/|  _ <| | |_ |    | | | |  | |  __| |  __| | |     ")
    print(" | |__| | |    | |_) | |__| |    | | | |__| | |____| |    | |____ ")
    print("  \____/|_|    |____/ \_____|    |_|  \____/|______|_|    |______|")
    print("                                                                  ")
    print("                                                                  ")

    # Initialize the database right before starting the server
    print("=" * 15)
    print("Initializing database...")
    print("=" * 15)
    init_db()

    print("Starting Flask server...")
    app.run(debug=True)
