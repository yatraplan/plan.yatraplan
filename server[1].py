"""
YatraPlan — Flask Backend (Render.com Ready)
- Serves index.html directly from Flask
- Uses SQLite database (persistent)
- Reads PORT from environment (required by Render)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os, datetime, json

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "yatraplan.db")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email           TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                phone           TEXT DEFAULT '',
                salt            TEXT DEFAULT '',
                hash            TEXT DEFAULT '',
                registered_at   TEXT DEFAULT '',
                failed_attempts INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                email TEXT PRIMARY KEY,
                trips TEXT DEFAULT '[]'
            )
        """)
        conn.commit()

init_db()

# ── Serve index.html at root ─────────────────────────────────────────────────
@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")

# ── API Routes ───────────────────────────────────────────────────────────────
@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "db": "sqlite"})

@app.route("/api/user/register", methods=["POST"])
def register():
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name")  or "").strip()
    phone = (data.get("phone") or "").strip()
    salt  = data.get("salt", "")
    hash_ = data.get("hash", "")
    if not email or not name:
        return jsonify({"error": "Missing required fields"}), 400
    with get_db() as conn:
        if conn.execute("SELECT email FROM users WHERE email=?", (email,)).fetchone():
            return jsonify({"error": "Email already exists"}), 200
        conn.execute(
            "INSERT INTO users (email,name,phone,salt,hash,registered_at,failed_attempts) VALUES(?,?,?,?,?,?,0)",
            (email, name, phone, salt, hash_, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    return jsonify({"ok": True, "email": email, "name": name})

@app.route("/api/user/get", methods=["POST"])
def get_user():
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return jsonify({"error": "User not found"}), 200
    return jsonify(dict(row))

@app.route("/api/user/update", methods=["POST"])
def update_user():
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    with get_db() as conn:
        if "failed_attempts" in data:
            conn.execute("UPDATE users SET failed_attempts=? WHERE email=?", (data["failed_attempts"], email))
        if "name" in data:
            conn.execute("UPDATE users SET name=? WHERE email=?", (data["name"], email))
        if "phone" in data:
            conn.execute("UPDATE users SET phone=? WHERE email=?", (data["phone"], email))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/user/delete", methods=["POST"])
def delete_user():
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE email=?", (email,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/users/all", methods=["GET"])
def all_users():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
    return jsonify({"users": {r["email"]: dict(r) for r in rows}})

@app.route("/api/trips/save", methods=["POST"])
def trips_save():
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    trips = json.dumps(data.get("trips", []), ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO trips(email,trips) VALUES(?,?) ON CONFLICT(email) DO UPDATE SET trips=excluded.trips",
            (email, trips)
        )
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/trips/get", methods=["POST"])
def trips_get():
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    with get_db() as conn:
        row = conn.execute("SELECT trips FROM trips WHERE email=?", (email,)).fetchone()
    return jsonify({"trips": json.loads(row["trips"]) if row else []})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"  YatraPlan → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
