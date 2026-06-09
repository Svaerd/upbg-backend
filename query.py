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
GET_PAYMENT_BY_ID = \
"""
SELECT * FROM payments WHERE payment_id = %s
"""

# UPDATE PAYMENT PROOF AND METHOD, set status to 'MENUNGGU VERIFIKASI'
UPDATE_PAYMENT_PROOF = \
"""
UPDATE payments 
SET metode = %s, status = 'MENUNGGU VERIFIKASI', tanggal_bayar = CURRENT_TIMESTAMP
WHERE payment_id = %s
"""

# GET ALL PENDING PAYMENTS FOR ADMIN
GET_PENDING_PAYMENTS = \
"""
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
APPROVE_PAYMENT = \
"""
UPDATE payments SET status = 'LUNAS' WHERE payment_id = %s
"""
