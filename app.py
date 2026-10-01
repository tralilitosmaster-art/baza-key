# app.py — Baza.Key Backend v1.2.0
import os
import json
import time
import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB = "baza_keys.db"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS keys (
        key TEXT PRIMARY KEY,
        plan TEXT,
        expires INTEGER,
        hwid_slots TEXT,
        tokens_total INTEGER,
        tokens_left INTEGER,
        refills INTEGER DEFAULT 0
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS postbacks (
        unique_id TEXT PRIMARY KEY,
        click_id TEXT,
        ip TEXT,
        timestamp INTEGER
    )""")
    con.commit()
    con.close()

@app.route("/")
def home():
    return "Baza.Key API is running"

@app.route("/health")
def health():
    return "OK"

@app.route("/validate", methods=["POST"])
def validate():
    data = request.json or {}
    key = data.get("key")
    hwid = data.get("hwid")

    con = sqlite3.connect(DB)
    row = con.execute("SELECT * FROM keys WHERE key=?", (key,)).fetchone()
    con.close()

    if not row:
        return jsonify({"valid": False, "reason": "invalid_key"})

    _, plan, expires, hwid_slots, tokens_total, tokens_left, refills = row

    # Check expiry
    if time.time() > expires:
        con = sqlite3.connect(DB)
        con.execute("UPDATE keys SET hwid_slots='[]' WHERE key=?", (key,))
        con.commit()
        con.close()
        return jsonify({"valid": False, "reason": "expired"})

    # Check tokens
    if tokens_left <= 0:
        return jsonify({"valid": False, "reason": "no_tokens"})

    # Check HWID slots
    slots = json.loads(hwid_slots or "[]")
    if hwid not in slots:
        if len(slots) >= 2:
            return jsonify({"valid": False, "reason": "hwid_limit"})
        slots.append(hwid)
        con = sqlite3.connect(DB)
        con.execute("UPDATE keys SET hwid_slots=? WHERE key=?", (json.dumps(slots), key))
        con.commit()
        con.close()

    return jsonify({
        "valid": True,
        "plan": plan,
        "tokens_left": tokens_left,
        "tokens_total": tokens_total,
        "expires": expires
    })

@app.route("/consume", methods=["POST"])
def consume():
    data = request.json or {}
    key = data.get("key")
    cost = int(data.get("cost", 0))

    con = sqlite3.connect(DB)
    row = con.execute("SELECT tokens_left FROM keys WHERE key=?", (key,)).fetchone()
    if not row or row[0] < cost:
        con.close()
        return jsonify({"ok": False, "reason": "no_tokens"})

    new_left = row[0] - cost
    con.execute("UPDATE keys SET tokens_left=? WHERE key=?", (new_left, key))
    con.commit()
    con.close()
    return jsonify({"ok": True, "tokens_left": new_left})

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json or {}
    plan = data.get("plan", "standard")
    amount = int(data.get("amount", 1))

    plan_config = {
        "free":     {"tokens": 1000,  "hours": 24},
        "standard": {"tokens": 10000, "hours": 24},
        "pro":      {"tokens": 50000, "hours": 72},
        "ultra":    {"tokens": 200000, "hours": 168},
    }
    cfg = plan_config.get(plan, plan_config["standard"])

    keys = []
    con = sqlite3.connect(DB)
    for _ in range(amount):
        import secrets
        suffix = secrets.token_hex(3).upper()
        key = f"BAZA_BCL_{suffix}"
        expires = int(time.time()) + cfg["hours"] * 3600
        con.execute("INSERT OR IGNORE INTO keys VALUES (?,?,?,?,?,?,?)",
                    (key, plan, expires, "[]", cfg["tokens"], cfg["tokens"], 0))
        keys.append(key)
    con.commit()
    con.close()

    return jsonify({"keys": keys, "plan": plan, "tokens": cfg["tokens"]})

@app.route("/api/lootlabs/postback", methods=["GET"])
def lootlabs_postback():
    click_id = request.args.get("click_id")
    ip = request.args.get("ip")
    unique_id = request.args.get("unique_id")

    if not unique_id:
        return "missing unique_id", 400

    # Prevent duplicates
    con = sqlite3.connect(DB)
    existing = con.execute("SELECT 1 FROM postbacks WHERE unique_id=?", (unique_id,)).fetchone()
    if existing:
        con.close()
        return "duplicate", 200

    con.execute("INSERT INTO postbacks VALUES (?,?,?,?)", (unique_id, click_id, ip, int(time.time())))
    con.commit()
    con.close()

    # Generate key for this user
    import secrets
    suffix = secrets.token_hex(3).upper()
    key = f"BAZA_BCL_{suffix}"
    expires = int(time.time()) + 24 * 3600

    con = sqlite3.connect(DB)
    con.execute("INSERT OR IGNORE INTO keys VALUES (?,?,?,?,?,?,?)",
                (key, "standard", expires, "[]", 10000, 10000, 0))
    con.commit()
    con.close()

    print(f"[Postback] User {click_id} (IP {ip}) completed task. Key: {key}")
    return key, 200

@app.route("/check/<key>")
def check_key(key):
    con = sqlite3.connect(DB)
    row = con.execute("SELECT * FROM keys WHERE key=?", (key,)).fetchone()
    con.close()
    if not row:
        return jsonify({"valid": False})
    _, plan, expires, hwid_slots, tokens_total, tokens_left, refills = row
    return jsonify({
        "valid": True,
        "plan": plan,
        "expires": expires,
        "tokens_left": tokens_left,
        "hwid_slots": json.loads(hwid_slots or "[]")
    })

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
