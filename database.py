"""
database.py  —  Local SQLite + Supabase REST sync for DGVCL
WAL mode enabled to prevent lock errors on PythonAnywhere.
"""
import os, sqlite3
from werkzeug.security import generate_password_hash
import supabase_api as supa

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'dgvcl.db')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dgvcl_users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL UNIQUE,
    password   TEXT NOT NULL,
    full_name  TEXT,
    role_id    INTEGER DEFAULT 2,
    active     INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dgvcl_divisions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    location   TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dgvcl_parties (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    contact     TEXT,
    email       TEXT,
    address     TEXT,
    gst         TEXT,
    division_id INTEGER,
    active      INTEGER DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (division_id) REFERENCES dgvcl_divisions(id)
);
CREATE TABLE IF NOT EXISTS dgvcl_roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dgvcl_permissions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id    INTEGER NOT NULL,
    page       TEXT NOT NULL,
    can_view   INTEGER DEFAULT 1,
    can_edit   INTEGER DEFAULT 0,
    can_delete INTEGER DEFAULT 0,
    FOREIGN KEY (role_id) REFERENCES dgvcl_roles(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS dgvcl_estimates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date              TEXT NOT NULL,
    party_id          INTEGER NOT NULL,
    division_id       INTEGER,
    scope_of_work     TEXT NOT NULL,
    kw_amount         REAL DEFAULT 1,
    security_deposit  REAL NOT NULL DEFAULT 0,
    fixed_charges     REAL NOT NULL DEFAULT 0,
    getco_charge      REAL NOT NULL DEFAULT 0,
    feeder_charge     REAL DEFAULT 0,
    agreement_charges REAL DEFAULT 0,
    created_by        INTEGER,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (party_id)    REFERENCES dgvcl_parties(id),
    FOREIGN KEY (division_id) REFERENCES dgvcl_divisions(id)
);
"""

def get_db():
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

# ── sync helpers ───────────────────────────────────────────────────────────────

def sync_insert(table, row: dict):
    if supa.is_enabled():
        try: supa.upsert_rows(table, [row])
        except Exception as e: print(f"[Sync] insert {table}: {e}")

def sync_update(table, row_id, data: dict):
    if supa.is_enabled():
        try: supa.update_row(table, row_id, data)
        except Exception as e: print(f"[Sync] update {table} {row_id}: {e}")

def sync_delete(table, row_id):
    if supa.is_enabled():
        try: supa.delete_row(table, row_id)
        except Exception as e: print(f"[Sync] delete {table} {row_id}: {e}")

def pull_from_cloud():
    if not supa.is_enabled(): return False
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    tables = ['dgvcl_users','dgvcl_divisions','dgvcl_parties','dgvcl_estimates']
    ok = sum(1 for t in tables if supa.pull_table(t, conn))
    conn.close()
    return ok == len(tables)

def push_all_to_cloud():
    if not supa.is_enabled(): return {}
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    tables = ['dgvcl_users','dgvcl_divisions','dgvcl_parties','dgvcl_estimates']
    results = {t: supa.push_table(t, conn) for t in tables}
    conn.close()
    return results

# ── init ───────────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(SQLITE_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)

    # Add location column if upgrading from old schema (replacing code)
    try:
        conn.execute("ALTER TABLE dgvcl_divisions ADD COLUMN location TEXT")
        conn.commit()
    except Exception:
        pass

    # Add kw_amount column if upgrading from old schema
    try:
        conn.execute("ALTER TABLE dgvcl_estimates ADD COLUMN kw_amount REAL DEFAULT 1")
        conn.commit()
    except Exception:
        pass

    # Migrate: add role_id column if upgrading from old schema with role TEXT
    try:
        conn.execute("ALTER TABLE dgvcl_users ADD COLUMN role_id INTEGER DEFAULT 2")
        conn.commit()
    except Exception:
        pass

    # Remove status column is not possible in SQLite but we just ignore it
    conn.commit()

    for name, location in [('Division 1 – Surat City','Surat City'),('Division 2 – Surat Rural','Surat Rural'),
                        ('Division 3 – Bardoli','Bardoli'),('Division 4 – Tapi','Tapi')]:
        try:
            conn.execute("INSERT INTO dgvcl_divisions (name,location) VALUES (?,?)", (name, location))
            conn.commit()
        except Exception:
            conn.rollback()

    # Seed default roles
    if not conn.execute("SELECT id FROM dgvcl_roles WHERE name='Admin'").fetchone():
        conn.execute("INSERT INTO dgvcl_roles (name,description) VALUES ('Admin','Full access to everything')")
        conn.execute("INSERT INTO dgvcl_roles (name,description) VALUES ('Manager','Can manage estimates and parties')")
        conn.execute("INSERT INTO dgvcl_roles (name,description) VALUES ('Viewer','Read-only access')")
        conn.commit()

        # Seed Admin permissions (full access to all pages)
        pages = ['dashboard','divisions','parties','estimates','reports','users','roles']
        for page in pages:
            conn.execute("INSERT INTO dgvcl_permissions (role_id,page,can_view,can_edit,can_delete) VALUES (1,?,1,1,1)", (page,))
        # Manager permissions
        for page in ['dashboard','divisions','parties','estimates','reports']:
            conn.execute("INSERT INTO dgvcl_permissions (role_id,page,can_view,can_edit,can_delete) VALUES (2,?,1,1,0)", (page,))
        # Viewer permissions
        for page in ['dashboard','divisions','parties','estimates','reports']:
            conn.execute("INSERT INTO dgvcl_permissions (role_id,page,can_view,can_edit,can_delete) VALUES (3,?,1,0,0)", (page,))
        conn.commit()

    if not conn.execute("SELECT id FROM dgvcl_users WHERE username='admin'").fetchone():
        conn.execute("INSERT INTO dgvcl_users (username,password,full_name,role_id) VALUES (?,?,?,?)",
                     ('admin', generate_password_hash('admin123'), 'System Administrator', 1))
        conn.commit()

    conn.close()
    print(f"[DB] DGVCL ready — {'Supabase ☁' if supa.is_enabled() else 'SQLite 💾'}")
