"""
supabase_api.py  —  Supabase REST API client for DGVCL
Keys always read from config.xlsx via config_loader — never hardcoded.
"""
import json, requests
import config_loader as cfg

def _url():  return cfg.get('SUPABASE_URL', '').rstrip('/')
def _key():  return cfg.get('SUPABASE_ANON_KEY', '')

def is_enabled():
    return bool(_url() and _key())

def reload_keys():
    cfg.reload()

TABLE_COLS = {
    'dgvcl_users':     ['id','username','password','full_name','role_id','active','created_at'],
    'dgvcl_roles':     ['id','name','description','created_at'],
    'dgvcl_permissions':['id','role_id','page','can_view','can_edit','can_delete'],
    'dgvcl_divisions': ['id','name','code','created_at'],
    'dgvcl_parties':   ['id','name','contact','email','address','gst','division_id','active','created_at'],
    'dgvcl_estimates': ['id','date','party_id','division_id','scope_of_work',
                        'security_deposit','fixed_charges','getco_charge',
                        'feeder_charge','agreement_charges','status','created_by','created_at'],
}

def _headers(prefer=''):
    k = _key()
    h = {'apikey': k, 'Authorization': f'Bearer {k}',
         'Content-Type': 'application/json', 'Accept': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    return h

def _rest(table):
    return f"{_url()}/rest/v1/{table}"

# ── READ ───────────────────────────────────────────────────────────────────────

def fetch_all(table) -> list:
    if not is_enabled(): return []
    try:
        r = requests.get(_rest(table), headers=_headers(),
                         params={'order': 'id.asc', 'limit': '10000'}, timeout=12)
        if r.status_code == 200: return r.json()
        print(f"[Supabase] fetch_all({table}) HTTP {r.status_code}: {r.text[:150]}")
        return []
    except Exception as e:
        print(f"[Supabase] fetch_all({table}): {e}"); return []

def fetch_filtered(table, filters: dict) -> list:
    """fetch_filtered('dgvcl_estimates', {'status': 'eq.Approved'})"""
    if not is_enabled(): return []
    try:
        params = {'order': 'id.desc', 'limit': '10000'}
        params.update(filters)
        r = requests.get(_rest(table), headers=_headers(), params=params, timeout=12)
        if r.status_code == 200: return r.json()
        return []
    except Exception as e:
        print(f"[Supabase] fetch_filtered({table}): {e}"); return []

# ── WRITE ──────────────────────────────────────────────────────────────────────

def upsert_rows(table, rows: list) -> bool:
    if not is_enabled() or not rows: return True
    clean = [{k: v for k, v in row.items() if v is not None or k == 'id'} for row in rows]
    try:
        r = requests.post(_rest(table),
                          headers=_headers('resolution=merge-duplicates,return=minimal'),
                          params={'on_conflict': 'id'},
                          data=json.dumps(clean), timeout=15)
        if r.status_code in (200, 201, 204): return True
        print(f"[Supabase] upsert({table}) HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[Supabase] upsert({table}): {e}"); return False

def insert_row(table, row: dict):
    """Insert one row, return the created row (with id) or None."""
    if not is_enabled(): return None
    try:
        r = requests.post(_rest(table),
                          headers=_headers('return=representation'),
                          data=json.dumps(row), timeout=12)
        if r.status_code in (200, 201):
            result = r.json()
            return result[0] if isinstance(result, list) else result
        print(f"[Supabase] insert({table}) HTTP {r.status_code}: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[Supabase] insert({table}): {e}"); return None

def update_row(table, row_id, data: dict) -> bool:
    if not is_enabled(): return True
    try:
        r = requests.patch(_rest(table),
                           headers=_headers('return=minimal'),
                           params={'id': f'eq.{row_id}'},
                           data=json.dumps(data), timeout=12)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[Supabase] update({table},{row_id}): {e}"); return False

def delete_row(table, row_id) -> bool:
    if not is_enabled(): return True
    try:
        r = requests.delete(_rest(table), headers=_headers('return=minimal'),
                            params={'id': f'eq.{row_id}'}, timeout=10)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[Supabase] delete({table},{row_id}): {e}"); return False

def push_table(table, sqlite_conn) -> bool:
    if not is_enabled(): return False
    cols = TABLE_COLS.get(table, [])
    if not cols: return False
    try:
        rows_raw = sqlite_conn.execute(f"SELECT {','.join(cols)} FROM {table}").fetchall()
        rows = [dict(zip(cols, list(r))) for r in rows_raw]
        return upsert_rows(table, rows)
    except Exception as e:
        print(f"[Supabase] push_table({table}): {e}"); return False

def pull_table(table, sqlite_conn) -> bool:
    if not is_enabled(): return False
    rows = fetch_all(table)
    if not rows: return True
    cols = TABLE_COLS.get(table, list(rows[0].keys()))
    try:
        sqlite_conn.execute(f"DELETE FROM {table}")
        for row in rows:
            vals = [row.get(c) for c in cols]
            ph   = ','.join(['?' for _ in cols])
            sqlite_conn.execute(
                f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({ph})", vals)
        sqlite_conn.commit()
        return True
    except Exception as e:
        print(f"[Supabase] pull_table({table}): {e}"); return False

# ── TEST ───────────────────────────────────────────────────────────────────────

def test_connection() -> tuple:
    url = _url(); key = _key()
    if not url: return False, "SUPABASE_URL missing in config.xlsx"
    if not key: return False, "SUPABASE_ANON_KEY missing in config.xlsx"
    try:
        r = requests.get(_rest('dgvcl_users'), headers=_headers(),
                         params={'limit': '1'}, timeout=8)
        if r.status_code == 200:
            return True, f"Connected ✓  →  {url}"
        elif r.status_code == 401:
            return False, "Unauthorized — use the Secret key (sb_secret_…)"
        elif r.status_code == 404:
            return False, "Tables not found — run the SQL setup in Supabase SQL Editor first."
        else:
            return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot reach Supabase — check internet connection."
    except Exception as e:
        return False, str(e)

# ── SQL TO PASTE IN SUPABASE ───────────────────────────────────────────────────

def create_tables_sql() -> str:
    return """\
-- DGVCL Estimate Portal: paste in Supabase → SQL Editor → Run ▶

CREATE TABLE IF NOT EXISTS dgvcl_users (
    id         SERIAL PRIMARY KEY,
    username   TEXT NOT NULL UNIQUE,
    password   TEXT NOT NULL,
    full_name  TEXT,
    role       TEXT DEFAULT 'user',
    active     INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dgvcl_divisions (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    code       TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dgvcl_parties (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    contact     TEXT,
    email       TEXT,
    address     TEXT,
    gst         TEXT,
    division_id INTEGER REFERENCES dgvcl_divisions(id),
    active      INTEGER DEFAULT 1,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dgvcl_estimates (
    id                SERIAL PRIMARY KEY,
    date              TEXT NOT NULL,
    party_id          INTEGER NOT NULL REFERENCES dgvcl_parties(id),
    division_id       INTEGER REFERENCES dgvcl_divisions(id),
    scope_of_work     TEXT NOT NULL,
    security_deposit  NUMERIC(15,2) NOT NULL DEFAULT 0,
    fixed_charges     NUMERIC(15,2) NOT NULL DEFAULT 0,
    getco_charge      NUMERIC(15,2) NOT NULL DEFAULT 0,
    feeder_charge     NUMERIC(15,2) DEFAULT 0,
    agreement_charges NUMERIC(15,2) DEFAULT 0,
    status            TEXT DEFAULT 'Pending',
    created_by        INTEGER,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Disable RLS so the secret key has full access
ALTER TABLE dgvcl_users     DISABLE ROW LEVEL SECURITY;
ALTER TABLE dgvcl_divisions DISABLE ROW LEVEL SECURITY;
ALTER TABLE dgvcl_parties   DISABLE ROW LEVEL SECURITY;
ALTER TABLE dgvcl_estimates DISABLE ROW LEVEL SECURITY;

-- Seed default divisions
INSERT INTO dgvcl_divisions (name, code) VALUES
  ('Division 1 – Surat City',  'DIV1'),
  ('Division 2 – Surat Rural', 'DIV2'),
  ('Division 3 – Bardoli',     'DIV3'),
  ('Division 4 – Tapi',        'DIV4')
ON CONFLICT (name) DO NOTHING;

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'dgvcl%';
"""
