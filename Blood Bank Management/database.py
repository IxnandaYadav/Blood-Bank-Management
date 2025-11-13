# Phase 2 — Database layer (SQLite)
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "blood_bank.db"

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]

COMPATIBILITY = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}

DONATION_EXPIRY_DAYS = 42
DONOR_ELIGIBILITY_DAYS = 90

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','staff')) DEFAULT 'staff'
    );

    CREATE TABLE IF NOT EXISTS donors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL CHECK(age > 0),
        gender TEXT CHECK(gender IN ('Male','Female','Other')),
        phone TEXT,
        address TEXT,
        blood_group TEXT NOT NULL,
        last_donation_date TEXT
    );

    CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL CHECK(age > 0),
        required_blood_group TEXT NOT NULL,
        quantity_needed INTEGER NOT NULL CHECK(quantity_needed > 0),
        hospital_name TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL,
        donation_code TEXT UNIQUE NOT NULL,
        blood_group TEXT NOT NULL,
        units INTEGER NOT NULL CHECK(units > 0),
        donation_date TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        FOREIGN KEY (donor_id) REFERENCES donors(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blood_group TEXT UNIQUE NOT NULL,
        available_units INTEGER NOT NULL DEFAULT 0 CHECK(available_units >= 0),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER NOT NULL,
        requested_blood_group TEXT NOT NULL,
        blood_group_issued TEXT NOT NULL,
        units INTEGER NOT NULL CHECK(units > 0),
        issue_date TEXT NOT NULL,
        compatible INTEGER NOT NULL CHECK(compatible IN (0,1)),
        status TEXT NOT NULL DEFAULT 'issued',
        FOREIGN KEY (recipient_id) REFERENCES recipients(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_donations_expiry ON donations(expiry_date);
    CREATE INDEX IF NOT EXISTS idx_issues_date ON issues(issue_date);
    """)
    cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    for bg in BLOOD_GROUPS:
        cur.execute("INSERT OR IGNORE INTO inventory (blood_group, available_units) VALUES (?, 0)", (bg,))
    conn.commit()
    conn.close()
    recalc_inventory()

def normalize_blood_group(bg: str) -> str:
    bg = (bg or "").strip().upper()
    if bg in BLOOD_GROUPS:
        return bg
    raise ValueError("Invalid blood group. Allowed: " + ", ".join(BLOOD_GROUPS))

def authenticate(username: str, password: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users WHERE username = ? AND password = ?", (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        return True, row["username"], row["role"]
    return False, None, None

# Donors
def add_donor(name, age, gender, phone, address, blood_group, last_donation_date=None):
    bg = normalize_blood_group(blood_group)
    if last_donation_date:
        try:
            datetime.strptime(last_donation_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("last_donation_date must be YYYY-MM-DD")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO donors (name, age, gender, phone, address, blood_group, last_donation_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name.strip(), int(age), gender, phone, address, bg, last_donation_date))
    conn.commit()
    conn.close()

def update_donor(donor_id, **fields):
    if not fields:
        return
    allowed = {"name","age","gender","phone","address","blood_group","last_donation_date"}
    set_parts = []
    values = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "blood_group":
            v = normalize_blood_group(v)
        if k == "age":
            v = int(v)
            if v <= 0: raise ValueError("Age must be positive")
        if k == "last_donation_date" and v:
            try:
                datetime.strptime(str(v), "%Y-%m-%d")
            except ValueError:
                raise ValueError("last_donation_date must be YYYY-MM-DD")
        set_parts.append(f"{k} = ?")
        values.append(v)
    if not set_parts:
        return
    values.append(int(donor_id))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE donors SET {', '.join(set_parts)} WHERE id = ?", values)
    conn.commit()
    conn.close()

def delete_donor(donor_id):
    conn = get_conn()
    conn.execute("DELETE FROM donors WHERE id = ?", (int(donor_id),))
    conn.commit()
    conn.close()

def list_donors():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM donors ORDER BY name").fetchall()
    conn.close()
    return rows

def eligible_donors():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM donors").fetchall()
    conn.close()
    eligible = []
    for r in rows:
        last = r["last_donation_date"]
        if not last:
            eligible.append(r)
            continue
        try:
            d = datetime.strptime(str(last), "%Y-%m-%d")
            if (datetime.now() - d).days >= DONOR_ELIGIBILITY_DAYS:
                eligible.append(r)
        except Exception:
            pass
    return eligible

# Recipients
def add_recipient(name, age, required_blood_group, quantity_needed, hospital_name):
    bg = normalize_blood_group(required_blood_group)
    conn = get_conn()
    conn.execute("""
        INSERT INTO recipients (name, age, required_blood_group, quantity_needed, hospital_name)
        VALUES (?, ?, ?, ?, ?)
    """, (name.strip(), int(age), bg, int(quantity_needed), hospital_name))
    conn.commit()
    conn.close()

def update_recipient(recipient_id, **fields):
    allowed = {"name","age","required_blood_group","quantity_needed","hospital_name"}
    set_parts, values = [], []
    for k,v in fields.items():
        if k not in allowed: continue
        if k == "required_blood_group":
            v = normalize_blood_group(v)
        if k in ("age","quantity_needed"):
            v = int(v)
            if v <= 0: raise ValueError(f"{k} must be positive")
        set_parts.append(f"{k} = ?")
        values.append(v)
    if not set_parts:
        return
    values.append(int(recipient_id))
    conn = get_conn()
    conn.execute(f"UPDATE recipients SET {', '.join(set_parts)} WHERE id = ?", values)
    conn.commit()
    conn.close()

def delete_recipient(recipient_id):
    conn = get_conn()
    conn.execute("DELETE FROM recipients WHERE id = ?", (int(recipient_id),))
    conn.commit()
    conn.close()

def list_recipients():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM recipients ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows

# Donations and Inventory
def record_donation(donor_id, blood_group, units, donation_date=None):
    bg = normalize_blood_group(blood_group)
    units = int(units)
    if units <= 0: raise ValueError("Units must be positive")
    donor_id = int(donor_id)
    now = datetime.now() if not donation_date else datetime.strptime(donation_date, "%Y-%m-%d")
    expiry = now + timedelta(days=DONATION_EXPIRY_DAYS)
    donation_code = f"D-{now.strftime('%Y%m%d%H%M%S')}-{donor_id}"
    conn = get_conn()
    cur = conn.cursor()
    d = cur.execute("SELECT id FROM donors WHERE id = ?", (donor_id,)).fetchone()
    if not d:
        conn.close()
        raise ValueError("Donor not found")
    cur.execute("""
        INSERT INTO donations (donor_id, donation_code, blood_group, units, donation_date, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (donor_id, donation_code, bg, units, now.strftime("%Y-%m-%d %H:%M:%S"), expiry.strftime("%Y-%m-%d %H:%M:%S")))
    cur.execute("UPDATE donors SET last_donation_date = ? WHERE id = ?", (now.strftime("%Y-%m-%d"), donor_id))
    conn.commit()
    conn.close()
    recalc_inventory()
    return donation_code

def recalc_inventory():
    conn = get_conn()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for bg in BLOOD_GROUPS:
        donated = cur.execute("""
            SELECT COALESCE(SUM(units),0) AS total
            FROM donations
            WHERE blood_group = ?
              AND expiry_date >= ?
        """, (bg, now_str)).fetchone()["total"]
        issued = cur.execute("""
            SELECT COALESCE(SUM(units),0) AS total
            FROM issues
            WHERE blood_group_issued = ?
        """, (bg,)).fetchone()["total"]
        available = max(0, int(donated) - int(issued))
        cur.execute("UPDATE inventory SET available_units = ?, updated_at = ? WHERE blood_group = ?",
                    (available, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bg))
    conn.commit()
    conn.close()

def list_inventory():
    recalc_inventory()
    conn = get_conn()
    rows = conn.execute("SELECT blood_group, available_units, updated_at FROM inventory ORDER BY blood_group").fetchall()
    conn.close()
    return rows

def low_stock_alerts(threshold=5):
    rows = list_inventory()
    low = []
    out = []
    for r in rows:
        if r["available_units"] == 0:
            out.append(r)
        elif r["available_units"] < threshold:
            low.append(r)
    return low, out

def record_issue(recipient_id, requested_blood_group, units):
    recipient_id = int(recipient_id)
    units = int(units)
    if units <= 0: raise ValueError("Units must be positive")
    requested = normalize_blood_group(requested_blood_group)
    conn = get_conn()
    cur = conn.cursor()
    rec = cur.execute("SELECT * FROM recipients WHERE id = ?", (recipient_id,)).fetchone()
    if not rec:
        conn.close()
        raise ValueError("Recipient not found")
    recalc_inventory()
    candidates = [requested] + [g for g in COMPATIBILITY[requested] if g != requested]
    issued_group = None
    for g in candidates:
        inv = cur.execute("SELECT available_units FROM inventory WHERE blood_group = ?", (g,)).fetchone()
        if inv and inv["available_units"] >= units:
            issued_group = g
            break
    compatible_flag = 1 if issued_group in COMPATIBILITY[requested] else 0
    if not issued_group:
        conn.close()
        raise ValueError("Insufficient compatible stock.")
    cur.execute("""
        INSERT INTO issues (recipient_id, requested_blood_group, blood_group_issued, units, issue_date, compatible, status)
        VALUES (?, ?, ?, ?, ?, ?, 'issued')
    """, (recipient_id, requested, issued_group, units, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), compatible_flag))
    conn.commit()
    conn.close()
    recalc_inventory()
    return issued_group

# Search & Reports
def search_donors(term=None, blood_group=None, location=None):
    term = (term or "").strip()
    location = (location or "").strip()
    params = []
    query = "SELECT * FROM donors WHERE 1=1"
    if term:
        query += " AND (name LIKE ? OR phone LIKE ?)"
        params += [f"%{term}%", f"%{term}%"]
    if blood_group:
        bg = normalize_blood_group(blood_group)
        query += " AND blood_group = ?"
        params.append(bg)
    if location:
        query += " AND address LIKE ?"
        params.append(f"%{location}%")
    query += " ORDER BY name"
    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows

def search_inventory(blood_group=None):
    recalc_inventory()
    conn = get_conn()
    if blood_group:
        bg = normalize_blood_group(blood_group)
        rows = conn.execute("SELECT * FROM inventory WHERE blood_group = ?", (bg,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM inventory ORDER BY blood_group").fetchall()
    conn.close()
    return rows

def report_totals():
    conn = get_conn()
    donors_total = conn.execute("SELECT COUNT(*) AS c FROM donors").fetchone()["c"]
    recalc_inventory()
    units_total = conn.execute("SELECT COALESCE(SUM(available_units),0) AS c FROM inventory").fetchone()["c"]
    conn.close()
    return donors_total, units_total

def report_most_requested_group():
    conn = get_conn()
    row = conn.execute("""
        SELECT requested_blood_group AS g, COUNT(*) AS cnt
        FROM issues
        GROUP BY requested_blood_group
        ORDER BY cnt DESC
        LIMIT 1
    """).fetchone()
    conn.close()
    if row:
        return row["g"], row["cnt"]
    return None, 0

def report_most_donated_group():
    conn = get_conn()
    row = conn.execute("""
        SELECT blood_group AS g, COALESCE(SUM(units),0) AS cnt
        FROM donations
        GROUP BY blood_group
        ORDER BY cnt DESC
        LIMIT 1
    """).fetchone()
    conn.close()
    if row:
        return row["g"], row["cnt"]
    return None, 0

def report_daily_donations():
    conn = get_conn()
    rows = conn.execute("""
        SELECT date(donation_date) AS day, COALESCE(SUM(units),0) AS units
        FROM donations
        GROUP BY date(donation_date)
        ORDER BY day DESC
    """).fetchall()
    conn.close()
    return rows

def report_monthly_donations():
    conn = get_conn()
    rows = conn.execute("""
        SELECT strftime('%Y-%m', donation_date) AS month, COALESCE(SUM(units),0) AS units
        FROM donations
        GROUP BY strftime('%Y-%m', donation_date)
        ORDER BY month DESC
    """).fetchall()
    conn.close()
    return rows

def match_compatible_donors(required_group):
    groups = COMPATIBILITY[normalize_blood_group(required_group)]
    return [d for d in list_donors() if d["blood_group"] in groups]