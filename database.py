import sqlite3
import hashlib
import secrets
from datetime import datetime

USER_DB = "users.db"
PRODUCT_DB = "repair_tracker.db"

def get_db(db_name):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"

def verify_password(password, stored_hash):
    try:
        salt, _ = stored_hash.split("$")
        return stored_hash == hash_password(password, salt)
    except:
        return False

def init_dbs():
    # Users Database
    with get_db(USER_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT
            )
        """)
        # Default users
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
                         ("admin", hash_password("admin123"), "admin", "Administrateur"))
            conn.execute("INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
                         ("user", hash_password("user123"), "user", "Utilisateur"))

    # Products/Jobs Database
    with get_db(PRODUCT_DB) as conn:
        conn.execute("""
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
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                prefix TEXT PRIMARY KEY,
                next_value INTEGER NOT NULL
            )
        """)

if __name__ == "__main__":
    init_dbs()
    print("Databases initialized.")
