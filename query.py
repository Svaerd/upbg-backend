# This contains the code for the query function, which is used to SQL query syntax.

# AMBIL USER DARI ID
GET_USER_BY_ID = """
SELECT user_id, nama, email, no_hp, tipe_user, nrp, instansi, created_at, password_hash
FROM users
WHERE user_id = %s
"""

# CEK USER BERDASARKAN EMAIL
GET_USER_BY_EMAIL = """
SELECT user_id, nama, email, no_hp, tipe_user, nrp, instansi, created_at, password_hash
FROM users
WHERE email = %s
"""

# INSERT USER BARU
INSERT_USER = """
INSERT INTO users (nama, email, password_hash, no_hp, tipe_user, nrp, instansi)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

# Count total pendaftar berdasarkan user_id
COUNT_REGISTRATIONS_BY_USER_ID = """
SELECT COUNT(*) AS total FROM registrations WHERE user_id = %s
"""

# Count total pembayaran berdasarkan user_id
COUNT_PAYMENTS_BY_USER_ID = """
SELECT COUNT(*) AS total
FROM payments p
INNER JOIN registrations r ON r.registration_id = p.registration_id
WHERE r.user_id = %s
"""

# Ambil 5 jadwal tes terbaru yang diikuti user berdasarkan user_id
GET_UPCOMING_SCHEDULES_BY_USER_ID = """
SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, s.lokasi, tt.nama_tes, r.status AS registration_status
FROM registrations r
INNER JOIN schedules s ON s.schedule_id = r.schedule_id
INNER JOIN test_types tt ON tt.test_type_id = s.test_type_id
WHERE r.user_id = %s
ORDER BY s.tanggal DESC, s.jam_mulai DESC
LIMIT 5
"""

# GET PAYMENT BY ID
GET_PAYMENT_BY_ID = """
SELECT * FROM payments WHERE payment_id = %s
"""

# UPDATE PAYMENT PROOF AND METHOD, set status to 'MENUNGGU VERIFIKASI'
UPDATE_PAYMENT_PROOF = """
UPDATE payments 
SET metode = %s, status = 'MENUNGGU VERIFIKASI', tanggal_bayar = CURRENT_TIMESTAMP
WHERE payment_id = %s
"""

# GET ALL PENDING PAYMENTS FOR ADMIN
GET_PENDING_PAYMENTS = """
SELECT p.payment_id, p.jumlah, p.metode, p.status as payment_status, p.tanggal_bayar,
       r.registration_id, u.nama, t.nama_tes
FROM payments p
JOIN registrations r ON p.registration_id = r.registration_id
JOIN users u ON r.user_id = u.user_id
JOIN schedules s ON r.schedule_id = s.schedule_id
JOIN test_types t ON s.test_type_id = t.test_type_id
WHERE p.status = 'MENUNGGU VERIFIKASI'
ORDER BY p.tanggal_bayar ASC
"""

# ADMIN APPROVE PAYMENT
APPROVE_PAYMENT = """
UPDATE payments SET status = 'LUNAS' WHERE payment_id = %s
"""

UPDATE_USER_PROFILE = """
UPDATE users 
SET nama = %s, no_hp = %s, nrp = %s, instansi = %s 
WHERE user_id = %s
"""

GET_ALL_USERS = "SELECT * FROM users ORDER BY created_at DESC"

INSERT_TEST_TYPE = """
INSERT INTO test_types (nama_tes, deskripsi, harga, masa_berlaku_sertifikat)
VALUES (%s, %s, %s, %s)
"""

GET_ALL_TEST_TYPES = "SELECT * FROM test_types ORDER BY test_type_id DESC"

DELETE_TEST_TYPE = "DELETE FROM test_types WHERE test_type_id = %s"

INSERT_SCHEDULE = """
INSERT INTO schedules (test_type_id, tanggal, jam_mulai, jam_selesai, lokasi, kuota, status)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

GET_ALL_SCHEDULES = """
SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, s.lokasi, s.kuota, s.status, t.nama_tes
FROM schedules s
JOIN test_types t ON s.test_type_id = t.test_type_id
ORDER BY s.tanggal DESC, s.jam_mulai DESC
"""

GET_TEST_TYPES_DROPDOWN = "SELECT test_type_id, nama_tes FROM test_types"

DELETE_SCHEDULE = "DELETE FROM schedules WHERE schedule_id = %s"

INSERT_EMPLOYEE = """
INSERT INTO employees (nama, email, no_hp, jabatan)
VALUES (%s, %s, %s, %s)
"""

GET_ALL_EMPLOYEES = "SELECT * FROM employees ORDER BY employee_id DESC"

DELETE_EMPLOYEE = "DELETE FROM employees WHERE employee_id = %s"

GET_SCHEDULE_BY_ID = """
SELECT s.schedule_id, s.tanggal, s.jam_mulai, s.jam_selesai, t.nama_tes
FROM schedules s
JOIN test_types t ON s.test_type_id = t.test_type_id
WHERE s.schedule_id = %s
"""

INSERT_SCHEDULE_SUPERVISOR = """
INSERT INTO schedule_supervisors (schedule_id, employee_id, peran)
VALUES (%s, %s, %s)
"""

GET_SCHEDULE_SUPERVISORS = """
SELECT ss.id, ss.peran, e.nama, e.email, e.jabatan
FROM schedule_supervisors ss
JOIN employees e ON ss.employee_id = e.employee_id
WHERE ss.schedule_id = %s
"""

GET_EMPLOYEES_DROPDOWN = "SELECT employee_id, nama, jabatan FROM employees"

DELETE_SCHEDULE_SUPERVISOR = "DELETE FROM schedule_supervisors WHERE id = %s"

GET_AVAILABLE_SCHEDULES = """
SELECT s.*, t.nama_tes, t.harga
FROM schedules s
JOIN test_types t ON s.test_type_id = t.test_type_id
WHERE s.status = 'TERSEDIA' AND s.kuota > 0
ORDER BY s.tanggal ASC, s.jam_mulai ASC
"""

GET_SCHEDULE_DETAILS = """
SELECT s.*, t.nama_tes, t.deskripsi, t.harga, t.masa_berlaku_sertifikat
FROM schedules s
JOIN test_types t ON s.test_type_id = t.test_type_id
WHERE s.schedule_id = %s
"""

CHECK_EXISTING_REGISTRATION = (
    "SELECT registration_id FROM registrations WHERE user_id = %s AND schedule_id = %s"
)

GET_SCHEDULE_BY_ID_SIMPLE = "SELECT * FROM schedules WHERE schedule_id = %s"

INSERT_REGISTRATION = "INSERT INTO registrations (user_id, schedule_id, status) VALUES (%s, %s, 'TERDAFTAR')"

INSERT_PAYMENT = "INSERT INTO payments (registration_id, jumlah, metode, status) VALUES (%s, %s, %s, 'PENDING')"

DECREMENT_SCHEDULE_QUOTA = (
    "UPDATE schedules SET kuota = kuota - 1 WHERE schedule_id = %s AND kuota > 0"
)

GET_USER_REGISTRATIONS = """
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
"""

GET_REGISTRATION_USER_ID = (
    "SELECT user_id FROM registrations WHERE registration_id = %s"
)

GET_REGISTRATION_FOR_EXAM = """
SELECT r.registration_id, r.user_id, r.schedule_id, t.nama_tes, t.test_type_id
FROM registrations r
JOIN schedules s ON r.schedule_id = s.schedule_id
JOIN test_types t ON s.test_type_id = t.test_type_id
WHERE r.registration_id = %s AND r.user_id = %s
"""
