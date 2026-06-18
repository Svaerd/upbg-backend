"""baseline_schema

Revision ID: b2975d4852ca
Revises:
Create Date: 2026-06-09 09:04:28.760595

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2975d4852ca"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Execute raw SQL directly
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            nama VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL DEFAULT '',
            no_hp VARCHAR(20),
            tipe_user VARCHAR(50),
            nrp VARCHAR(50),
            instansi VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS test_types (
            test_type_id INT AUTO_INCREMENT PRIMARY KEY,
            nama_tes VARCHAR(255) NOT NULL,
            deskripsi TEXT,
            harga DECIMAL(10, 2),
            masa_berlaku_sertifikat INT
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id INT AUTO_INCREMENT PRIMARY KEY,
            nama VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            no_hp VARCHAR(20),
            jabatan VARCHAR(100)
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id INT AUTO_INCREMENT PRIMARY KEY,
            test_type_id INT NOT NULL,
            tanggal DATE,
            jam_mulai TIME,
            jam_selesai TIME,
            lokasi VARCHAR(255),
            kuota INT,
            status VARCHAR(50),
            FOREIGN KEY (test_type_id) REFERENCES test_types(test_type_id) ON DELETE CASCADE
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS schedule_supervisors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            schedule_id INT NOT NULL,
            employee_id INT NOT NULL,
            peran VARCHAR(100),
            FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            registration_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            schedule_id INT NOT NULL,
            tanggal_daftar DATETIME DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id) ON DELETE CASCADE
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INT AUTO_INCREMENT PRIMARY KEY,
            registration_id INT UNIQUE NOT NULL,
            jumlah DECIMAL(10, 2),
            metode VARCHAR(50),
            tanggal_bayar DATETIME,
            status VARCHAR(50),
            FOREIGN KEY (registration_id) REFERENCES registrations(registration_id) ON DELETE CASCADE
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            result_id INT AUTO_INCREMENT PRIMARY KEY,
            registration_id INT UNIQUE NOT NULL,
            total_score INT,
            listening_score INT,
            reading_score INT,
            structure_score INT,
            issue_date DATE,
            remarks TEXT,
            FOREIGN KEY (registration_id) REFERENCES registrations(registration_id) ON DELETE CASCADE
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            certificate_id INT AUTO_INCREMENT PRIMARY KEY,
            result_id INT UNIQUE NOT NULL,
            nomor_sertifikat VARCHAR(255) UNIQUE NOT NULL,
            tanggal_terbit DATE,
            file_url VARCHAR(255),
            FOREIGN KEY (result_id) REFERENCES test_results(result_id) ON DELETE CASCADE
        );
    """)


def downgrade() -> None:
    # Drop tables in reverse order of creation to respect foreign key constraints
    op.execute("DROP TABLE IF EXISTS certificates;")
    op.execute("DROP TABLE IF EXISTS test_results;")
    op.execute("DROP TABLE IF EXISTS payments;")
    op.execute("DROP TABLE IF EXISTS registrations;")
    op.execute("DROP TABLE IF EXISTS schedule_supervisors;")
    op.execute("DROP TABLE IF EXISTS schedules;")
    op.execute("DROP TABLE IF EXISTS employees;")
    op.execute("DROP TABLE IF EXISTS test_types;")
    op.execute("DROP TABLE IF EXISTS users;")
