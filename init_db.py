import sqlite3
import hashlib
import secrets

DB_PATH = "repair_tracker.db"

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"

def ensure_database():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT
        );

        CREATE TABLE IF NOT EXISTS counters (
            prefix TEXT PRIMARY KEY,
            next_value INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            product_number TEXT NOT NULL,
            scan_reference TEXT,
            customer_name TEXT,
            phone_number TEXT,
            device_type TEXT,
            status TEXT,
            brand_model TEXT,
            serial_number TEXT,
            received_date TEXT,
            delivery_decision TEXT,
            delivered_date TEXT,
            amount TEXT,
            paid_status TEXT,
            problem TEXT,
            repair_done TEXT,
            notes TEXT,
            accessories TEXT,
            other_accessory TEXT,
            device_condition TEXT,
            condition_remarks TEXT,
            technician_name TEXT,
            return_condition TEXT,
            is_subcontracted TEXT,
            subcontract_company TEXT,
            subcontract_sent_date TEXT,
            subcontract_return_status TEXT,
            subcontract_returned_date TEXT,
            subcontract_notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )

    cursor = conn.execute("SELECT COUNT(*) AS total FROM users")
    existing = cursor.fetchone()[0]
    if existing == 0:
      conn.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            ("admin", password_hash("admin123"), "admin", "Administrateur"),
        )
      conn.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            ("user", password_hash("user123"), "user", "Utilisateur"),
        )
      print("Default users created: admin/admin123 and user/user123")

    conn.commit()
    conn.close()
    print("Database schema ensured.")

if __name__ == "__main__":
    ensure_database()
