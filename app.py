# app.py — Baza.Key Backend v1.2.2
import os
import json
import time
import sqlite3
import secrets
import requests
from flask import Flask, request, jsonify, render_template_string

try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False

app = Flask(__name__)
DB = "baza_keys.db"

LOOTLABS_API_KEY = os.environ.get("LOOTLABS_API_KEY", "")
LOOTLABS_BASE_LINK = os.environ.get("LOOTLABS_BASE_LINK", "")
FERNET_KEY = os.environ.get("FERNET_KEY", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "changeme123")
REQUIRED_COMPLETIONS = 2
FREE_TOKENS = 1000
FREE_HOURS = 24

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS keys (
        key TEXT PRIMARY KEY,
        plan TEXT,
        expires INTEGER,
        hwid_slots TEXT,
        tokens_total INTEGER,
        tokens_left INTEGER,
        refills INTEGER DEFAULT 0,
        created INTEGER
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS postbacks (
        click_id TEXT PRIMARY KEY,
        completions INTEGER DEFAULT 0,
        last_ip TEXT,
        last_ts INTEGER,
        keys_issued INTEGER DEFAULT 0,
        issued_key TEXT
    )""")
    con.commit()
    con.close()

BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #000; color: #fff; min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
    background: radial-gradient(ellipse at top, #3a0000 0%, #000 60%);
    padding: 20px;
}
.card {
    width: 100%; max-width: 460px;
    background: linear-gradient(135deg, #000 0%, #1a0000 100%);
    border: 1.5px solid #ff2828; border-radius: 14px; padding: 36px;
    box-shadow: 0 0 60px rgba(255,40,40,0.35), 0 0 20px rgba(255,40,40,0.15) inset;
    position: relative; overflow: hidden;
}
.card::before {
    content: ''; position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: linear-gradient(45deg, transparent 30%, rgba(255,40,40,0.08) 50%, transparent 70%);
    animation: shine 6s linear infinite; pointer-events: none;
}
@keyframes shine {
    0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}
.logo {
    font-size: 34px; font-weight: 800;
    background: linear-gradient(90deg, #b40000, #ff2828, #b40000);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 8px; letter-spacing: 1px;
}
.subtitle {
    text-align: center; color: #c89696; font-size: 14px;
    margin-bottom: 8px; line-height: 1.5;
}
.tagline {
    text-align: center; color: #ff6060; font-size: 13px;
    margin-bottom: 24px; font-weight: 600;
}
.discord {
    display: block; margin-top: 12px; padding: 14px;
    background: linear-gradient(135deg, #28283a, #5865f2);
    border-radius: 8px; text-align: center; text-decoration: none;
    color: #fff; font-weight: 700; font-size: 14px;
    transition: transform 0.15s;
}
.discord:hover { transform: translateY(-1px); }
button {
    width: 100%; padding: 14px;
    background: linear-gradient(135deg, #8b0000, #ff2828);
    border: none; border-radius: 8px; color: #fff;
    font-size: 15px; font-weight: 700; cursor: pointer;
    transition: transform 0.15s, box-shadow 0.2s;
    letter-spacing: 0.5px; margin-bottom: 8px;
}
button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(255,40,40,0.5);
}
button:active { transform: translateY(0); }
.badge {
    display: inline-block; padding: 3px 10px;
    background: rgba(255,40,40,0.15); border: 1px solid #b40000;
    border-radius: 12px; color: #ff6060; font-size: 11px;
    margin-bottom: 16px; font-weight: 600;
}
.info {
    padding: 14px; background: #0a0000; border: 1px solid #4a0000;
    border-radius: 8px; color: #c89696; font-size: 13px;
    line-height: 1.6; text-align: center; margin-bottom: 16px;
}
.info b { color: #ff6060; }
.status {
    color: #c89696; font-size: 12px; text-align: center;
    margin-top: 12px; min-height: 16px;
}
.result {
    margin-top: 16px; padding: 16px; background: #0a0000;
    border: 1px solid #4a0000; border-radius: 8px;
    font-family: 'Courier New', monospace; font-size: 13px;
    word-break: break-all; display: none;
}
.result.show { display: block; }
.result .key {
    color: #40dc64; font-weight: 700; font-size: 15px;
    display: block; margin-bottom: 8px;
}
"""

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Baza.Key — BCL</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
    <div class="card">
        <div class="badge">BAZA.KEY</div>
        <div class="logo">Baza.Key</div>
        <div class="subtitle">BCL — best decompiler luau script.</div>
        <div class="tagline">Get to key! (This is fast)</div>

        <button onclick="getLootLink()">Get Key via LootLabs</button>
        <a class="discord" href="https://discord.gg/vVFeyntpa" target="_blank">
            Join to Discord Community
        </a>

        <div class="status" id="status"></div>
        <div class="result" id="result"></div>
    </div>

    <script>
        async function getLootLink() {
            const status = document.getElementById('status');
            const result = document.getElementById('result');
            status.textContent = 'Generating link...';
            result.classList.remove('show');

            try {
                const res = await fetch('/api/getlink');
                const data = await res.json();

                if (data.link) {
                    status.textContent = 'Redirecting to LootLabs...';
                    window.location.href = data.link;
                } else if (data.key) {
                    result.innerHTML =
                        '<span class="key">' + data.key + '</span>' +
                        'Save this key. Expires in 24h.';
                    result.classList.add('show');
                    status.textContent = '';
                } else {
                    status.textContent = 'Error: ' + (data.error || 'try again');
                }
            } catch (e) {
                status.textContent = 'Network error. Refresh and retry.';
            }
        }
    </script>
</body>
</html>
"""

ADMIN_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Baza.Key — Admin</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
    <div class="card">
        <div class="badge">ADMIN</div>
        <div class="logo">Admin</div>
        <div class="subtitle">Bulk key generation</div>

        <input type="number" id="amount" value="10" min="1" max="100"
               placeholder="Amount"
               style="width:100%;padding:14px;background:#000;border:1px solid #b40000;
                      border-radius:8px;color:#fff;font-size:14px;margin-bottom:12px;"
        />
        <input type="password" id="token" placeholder="Admin token"
               style="width:100%;padding:14px;background:#000;border:1px solid #b40000;
                      border-radius:8px;color:#fff;font-size:14px;margin-bottom:12px;"
        />
        <button onclick="bulkGen()">Generate</button>

        <div class="status" id="status"></div>
        <div class="result" id="result"></div>
    </div>

    <script>
        async function bulkGen() {
            const amount = document.getElementById('amount').value;
            const token = document.getElementById('token').value;
            const status = document.getElementById('status');
            const result = document.getElementById('result');
            status.textContent = 'Generating...';
            result.classList.remove('show');

            try {
                const res = await fetch('/api/admin/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({plan: 'free', amount: parseInt(amount), token})
                });
                const data = await res.json();
                if (data.keys) {
                    result.innerHTML = '<span class="key">' + data.keys.length + ' keys</span>' +
                        data.keys.join('<br>');
                    result.classList.add('show');
                    status.textContent = '';
                } else {
                    status.textContent = data.error || 'Failed';
                }
            } catch (e) {
                status.textContent = 'Network error';
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/admin")
def admin():
    return render_template_string(ADMIN_HTML)

@app.route("/health")
def health():
    return "OK"

@app.route("/api/getlink")
def api_getlink():
    if not LOOTLABS_API_KEY or not LOOTLABS_BASE_LINK:
        return jsonify({"error": "LootLabs not configured"}), 500

    try:
        r = requests.get(
            "https://creators.lootlabs.gg/api/public/url_encryptor",
            params={
                "destination_url": "https://baza-key.onrender.com",
                "api_token": LOOTLABS_API_KEY
            },
            timeout=8
        )
        data = r.json()
        if data.get("type") in ("created", "fetched"):
            encrypted = data["message"]
            puid = request.args.get("puid") or secrets.token_hex(8)
            final_link = f"{LOOTLABS_BASE_LINK}&puid={puid}&data={encrypted}"
            return jsonify({"link": final_link})
        return jsonify({"error": data.get("message", "encrypt failed")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/getscript", methods=["POST"])
def api_getscript():
    data = request.json or {}
    key = data.get("key")
    hwid = data.get("hwid")

    con = sqlite3.connect(DB)
    row = con.execute("SELECT * FROM keys WHERE key=?", (key,)).fetchone()
    con.close()

    if not row:
        return jsonify({"error": "invalid_key"}), 403

    _, plan, expires, hwid_slots, tokens_total, tokens_left, refills, created = row
    if time.time() > expires:
        return jsonify({"error": "expired"}), 403
    if tokens_left <= 0:
        return jsonify({"error": "no_tokens"}), 403

    slots = json.loads(hwid_slots or "[]")
    if hwid and hwid not in slots:
        if len(slots) >= 2:
            return jsonify({"error": "hwid_limit"}), 403
        slots.append(hwid)
        con = sqlite3.connect(DB)
        con.execute("UPDATE keys SET hwid_slots=? WHERE key=?", (json.dumps(slots), key))
        con.commit()
        con.close()

    try:
        if FERNET_AVAILABLE and FERNET_KEY:
            cipher = Fernet(FERNET_KEY.encode())
            with open("main.lua.enc", "rb") as f:
                encrypted = f.read()
            decrypted = cipher.decrypt(encrypted)
            return decrypted, 200, {"Content-Type": "text/plain"}
        else:
            with open("main.lua", "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/plain"}
    except Exception as e:
        return jsonify({"error": "script_read_failed", "detail": str(e)}), 500

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

    _, plan, expires, hwid_slots, tokens_total, tokens_left, refills, created = row
    if time.time() > expires:
        return jsonify({"valid": False, "reason": "expired"})
    if tokens_left <= 0:
        return jsonify({"valid": False, "reason": "no_tokens"})

    slots = json.loads(hwid_slots or "[]")
    if hwid and hwid not in slots:
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

@app.route("/api/lootlabs/postback", methods=["GET"])
def lootlabs_postback():
    click_id = request.args.get("click_id")
    ip = request.args.get("ip")

    if not click_id:
        return "missing click_id", 400

    con = sqlite3.connect(DB)
    row = con.execute("SELECT completions, keys_issued, issued_key FROM postbacks WHERE click_id=?",
                      (click_id,)).fetchone()

    if row:
        completions, keys_issued, issued_key = row
    else:
        completions, keys_issued, issued_key = 0, 0, None

    if keys_issued >= 1 and issued_key:
        con.close()
        return issued_key, 200

    completions += 1

    if completions < REQUIRED_COMPLETIONS:
        con.execute("""INSERT INTO postbacks (click_id, completions, last_ip, last_ts, keys_issued)
                       VALUES (?,?,?,?,0)
                       ON CONFLICT(click_id) DO UPDATE SET
                       completions=excluded.completions,
                       last_ip=excluded.last_ip,
                       last_ts=excluded.last_ts""",
                    (click_id, completions, ip, int(time.time())))
        con.commit()
        con.close()
        print(f"[Postback] {click_id} → {completions}/{REQUIRED_COMPLETIONS}")
        return f"registered {completions}/{REQUIRED_COMPLETIONS}", 200

    suffix = secrets.token_hex(3).upper()
    key = f"BAZA_BCL_{suffix}"
    expires = int(time.time()) + FREE_HOURS * 3600

    con.execute("INSERT INTO keys VALUES (?,?,?,?,?,?,?,?)",
                (key, "free", expires, "[]", FREE_TOKENS, FREE_TOKENS, 0, int(time.time())))
    con.execute("""INSERT INTO postbacks (click_id, completions, last_ip, last_ts, keys_issued, issued_key)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(click_id) DO UPDATE SET
                   completions=excluded.completions,
                   last_ip=excluded.last_ip,
                   last_ts=excluded.last_ts,
                   keys_issued=excluded.keys_issued,
                   issued_key=excluded.issued_key""",
                (click_id, completions, ip, int(time.time()), 1, key))
    con.commit()
    con.close()

    print(f"[Postback] {click_id} → {completions}/{REQUIRED_COMPLETIONS} → KEY={key}")
    return key, 200

@app.route("/api/admin/generate", methods=["POST"])
def admin_generate():
    data = request.json or {}
    if data.get("token") != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401

    amount = min(int(data.get("amount", 1)), 100)
    keys = []
    con = sqlite3.connect(DB)
    for _ in range(amount):
        suffix = secrets.token_hex(3).upper()
        key = f"BAZA_BCL_{suffix}"
        expires = int(time.time()) + FREE_HOURS * 3600
        con.execute("INSERT OR IGNORE INTO keys VALUES (?,?,?,?,?,?,?,?)",
                    (key, "free", expires, "[]", FREE_TOKENS, FREE_TOKENS, 0, int(time.time())))
        keys.append(key)
    con.commit()
    con.close()
    return jsonify({"keys": keys})

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

