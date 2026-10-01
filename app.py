# app.py — Baza.Key Backend + Web UI v1.2.0
# Logic: 2x LootLabs completion → key issued. Free plan only.
import os
import json
import time
import sqlite3
import secrets
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB = "baza_keys.db"

# ============================================================
# DATABASE
# ============================================================
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
        keys_issued INTEGER DEFAULT 0
    )""")
    con.commit()
    con.close()

# ============================================================
# CSS (shared)
# ============================================================
BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #000;
    color: #fff;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(ellipse at top, #3a0000 0%, #000 60%);
    padding: 20px;
}
.card {
    width: 100%;
    max-width: 440px;
    background: linear-gradient(135deg, #000 0%, #1a0000 100%);
    border: 1.5px solid #ff2828;
    border-radius: 14px;
    padding: 32px;
    box-shadow: 0 0 60px rgba(255, 40, 40, 0.35), 0 0 20px rgba(255, 40, 40, 0.15) inset;
    position: relative;
    overflow: hidden;
}
.card::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: linear-gradient(45deg, transparent 30%, rgba(255, 40, 40, 0.08) 50%, transparent 70%);
    animation: shine 6s linear infinite;
    pointer-events: none;
}
@keyframes shine {
    0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}
.logo {
    font-size: 32px;
    font-weight: 800;
    background: linear-gradient(90deg, #b40000, #ff2828, #b40000);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 6px;
    letter-spacing: 1px;
}
.subtitle {
    text-align: center;
    color: #c89696;
    font-size: 13px;
    margin-bottom: 24px;
}
.input-group { margin-bottom: 14px; }
input, select {
    width: 100%;
    padding: 14px 16px;
    background: #000;
    border: 1px solid #b40000;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    font-family: 'Courier New', monospace;
}
input:focus, select:focus {
    border-color: #ff2828;
    box-shadow: 0 0 12px rgba(255, 40, 40, 0.5);
}
input::placeholder { color: #703030; }
button {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #8b0000, #ff2828);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.2s;
    letter-spacing: 0.5px;
    margin-top: 8px;
}
button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(255, 40, 40, 0.5);
}
button:active { transform: translateY(0); }
.result {
    margin-top: 20px;
    padding: 16px;
    background: #0a0000;
    border: 1px solid #4a0000;
    border-radius: 8px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    word-break: break-all;
    display: none;
}
.result.show { display: block; }
.result .key {
    color: #40dc64;
    font-weight: 700;
    font-size: 15px;
    display: block;
    margin-bottom: 8px;
}
.result .meta { color: #c89696; font-size: 12px; line-height: 1.6; }
.error {
    color: #ff2828;
    font-size: 13px;
    margin-top: 10px;
    text-align: center;
    display: none;
}
.error.show { display: block; }
.discord {
    display: block;
    margin-top: 20px;
    padding: 12px;
    background: linear-gradient(135deg, #28283a, #5865f2);
    border-radius: 8px;
    text-align: center;
    text-decoration: none;
    color: #fff;
    font-weight: 700;
    font-size: 14px;
    transition: transform 0.15s;
}
.discord:hover { transform: translateY(-1px); }
.badge {
    display: inline-block;
    padding: 3px 10px;
    background: rgba(255, 40, 40, 0.15);
    border: 1px solid #b40000;
    border-radius: 12px;
    color: #ff6060;
    font-size: 11px;
    margin-bottom: 16px;
    font-weight: 600;
}
.plan-box {
    padding: 14px 16px;
    background: #0a0000;
    border: 1px solid #4a0000;
    border-radius: 8px;
    color: #c89696;
    text-align: center;
    font-family: 'Courier New', monospace;
    font-size: 13px;
}
.step {
    display: inline-block;
    width: 24px;
    height: 24px;
    background: linear-gradient(135deg, #8b0000, #ff2828);
    border-radius: 50%;
    text-align: center;
    line-height: 24px;
    font-weight: 700;
    font-size: 13px;
    margin-right: 8px;
}
.info-line {
    color: #c89696;
    font-size: 13px;
    text-align: center;
    margin: 16px 0;
    line-height: 1.6;
}
"""

# ============================================================
# HTML — LANDING (index)
# ============================================================
INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Baza.Key — Get your key</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
    <div class="card">
        <div class="badge">BAZA.KEY v1.2.0</div>
        <div class="logo">Baza.Key</div>
        <div class="subtitle">Free access key for BCL</div>

        <div class="input-group">
            <div class="plan-box">FREE — 1000 tokens / 24h</div>
        </div>
        <div class="input-group">
            <input type="text" id="hwid" placeholder="Your HWID (optional)" />
        </div>

        <button onclick="generate()">Generate Key</button>

        <div class="result" id="result"></div>
        <div class="error" id="error"></div>

        <a class="discord" href="https://discord.gg/vVFeyntpa" target="_blank">Join in Baza Community</a>
    </div>

    <script>
        async function generate() {
            const hwid = document.getElementById('hwid').value.trim();
            const result = document.getElementById('result');
            const error = document.getElementById('error');

            result.classList.remove('show');
            error.classList.remove('show');

            try {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plan: 'free', hwid })
                });
                const data = await res.json();

                if (data.key) {
                    const exp = new Date(data.expires * 1000);
                    result.innerHTML =
                        '<span class="key">' + data.key + '</span>' +
                        '<div class="meta">' +
                        'Plan: FREE<br>' +
                        'Tokens: ' + data.tokens + '<br>' +
                        'Expires: ' + exp.toLocaleString() +
                        '</div>';
                    result.classList.add('show');
                } else {
                    error.textContent = data.error || 'Generation failed';
                    error.classList.add('show');
                }
            } catch (e) {
                error.textContent = 'Network error: ' + e.message;
                error.classList.add('show');
            }
        }
    </script>
</body>
</html>
"""

# ============================================================
# HTML — STEP 2 (after first LootLabs completion)
# ============================================================
STEP2_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Baza.Key — Step 2/2</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
    <div class="card">
        <div class="badge">STEP 1/2 COMPLETE</div>
        <div class="logo">Almost there</div>
        <div class="subtitle">One more step to get your key</div>

        <div class="info-line">
            <span class="step">2</span>Pass the tasks one more time to unlock your key.
        </div>

        <div class="input-group">
            <input type="text" id="puid" placeholder="Your user ID (same as in link)" />
        </div>

        <button onclick="nextStep()">Continue to Step 2/2</button>

        <div class="result" id="result"></div>
        <div class="error" id="error"></div>

        <a class="discord" href="https://discord.gg/vVFeyntpa" target="_blank">Join in Baza Community</a>
    </div>

    <script>
        async function nextStep() {
            const puid = document.getElementById('puid').value.trim();
            const error = document.getElementById('error');
            const result = document.getElementById('result');

            error.classList.remove('show');
            result.classList.remove('show');

            if (!puid) {
                error.textContent = 'Enter your user ID';
                error.classList.add('show');
                return;
            }

            // Redirect user back to LootLabs link for second completion
            // In real usage, this would be set to your second loot-link
            window.location.href = 'https://loot-link.com/s?SECOND_LINK&puid=' + encodeURIComponent(puid);
        }
    </script>
</body>
</html>
"""

# ============================================================
# HTML — ADMIN
# ============================================================
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
        <div class="logo">Baza.Key Admin</div>
        <div class="subtitle">Bulk key generation</div>

        <div class="input-group">
            <select id="plan">
                <option value="free" selected>Free (1 000)</option>
                <option value="standard">Standard (10 000)</option>
            </select>
        </div>
        <div class="input-group">
            <input type="number" id="amount" placeholder="Amount" value="10" min="1" max="1000" />
        </div>
        <div class="input-group">
            <input type="password" id="token" placeholder="Admin token" />
        </div>

        <button onclick="bulkGen()">Generate Bulk</button>

        <div class="result" id="result"></div>
        <div class="error" id="error"></div>
    </div>

    <script>
        async function bulkGen() {
            const plan = document.getElementById('plan').value;
            const amount = document.getElementById('amount').value;
            const token = document.getElementById('token').value;
            const result = document.getElementById('result');
            const error = document.getElementById('error');

            result.classList.remove('show');
            error.classList.remove('show');

            try {
                const res = await fetch('/api/admin/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plan, amount: parseInt(amount), token })
                });
                const data = await res.json();

                if (data.keys) {
                    result.innerHTML = '<span class="key">' + data.keys.length + ' keys generated</span>' +
                        '<div class="meta">' + data.keys.join('<br>') + '</div>';
                    result.classList.add('show');
                } else {
                    error.textContent = data.error || 'Failed';
                    error.classList.add('show');
                }
            } catch (e) {
                error.textContent = 'Network error: ' + e.message;
                error.classList.add('show');
            }
        }
    </script>
</body>
</html>
"""

# ============================================================
# PLAN CONFIG
# ============================================================
PLAN_CONFIG = {
    "free":     {"tokens": 1000,   "hours": 24},
    "standard": {"tokens": 10000,  "hours": 24},
}

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "changeme123")
REQUIRED_COMPLETIONS = 2  # User must pass LootLabs 2 times

# ============================================================
# ROUTES — WEB UI
# ============================================================
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/step2")
def step2():
    return render_template_string(STEP2_HTML)

@app.route("/admin")
def admin():
    return render_template_string(ADMIN_HTML)

@app.route("/health")
def health():
    return "OK"

# ============================================================
# ROUTES — PUBLIC API
# ============================================================
@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.json or {}
    hwid = data.get("hwid", "")

    cfg = PLAN_CONFIG["free"]
    suffix = secrets.token_hex(3).upper()
    key = f"BAZA_BCL_{suffix}"
    expires = int(time.time()) + cfg["hours"] * 3600

    slots = []
    if hwid:
        slots.append(hwid)

    con = sqlite3.connect(DB)
    con.execute("INSERT INTO keys VALUES (?,?,?,?,?,?,?,?)",
                (key, "free", expires, json.dumps(slots),
                 cfg["tokens"], cfg["tokens"], 0, int(time.time())))
    con.commit()
    con.close()

    return jsonify({
        "key": key,
        "plan": "free",
        "tokens": cfg["tokens"],
        "expires": expires
    })

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
        con = sqlite3.connect(DB)
        con.execute("UPDATE keys SET hwid_slots='[]' WHERE key=?", (key,))
        con.commit()
        con.close()
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

# ============================================================
# ROUTES — ADMIN API
# ============================================================
@app.route("/api/admin/generate", methods=["POST"])
def admin_generate():
    data = request.json or {}
    token = data.get("token")
    plan = data.get("plan", "free")
    amount = int(data.get("amount", 1))

    if token != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    if plan not in PLAN_CONFIG:
        return jsonify({"error": "invalid_plan"}), 400

    cfg = PLAN_CONFIG[plan]
    keys = []
    con = sqlite3.connect(DB)
    for _ in range(amount):
        suffix = secrets.token_hex(3).upper()
        key = f"BAZA_BCL_{suffix}"
        expires = int(time.time()) + cfg["hours"] * 3600
        con.execute("INSERT OR IGNORE INTO keys VALUES (?,?,?,?,?,?,?,?)",
                    (key, plan, expires, "[]", cfg["tokens"], cfg["tokens"], 0, int(time.time())))
        keys.append(key)
    con.commit()
    con.close()
    return jsonify({"keys": keys, "plan": plan, "tokens": cfg["tokens"]})

# ============================================================
# ROUTES — LOOTLABS POSTBACK (2 completions required)
# ============================================================
@app.route("/api/lootlabs/postback", methods=["GET"])
def lootlabs_postback():
    click_id = request.args.get("click_id")
    ip = request.args.get("ip")
    unique_id = request.args.get("unique_id")

    if not click_id:
        return "missing click_id", 400

    con = sqlite3.connect(DB)
    row = con.execute("SELECT completions, keys_issued FROM postbacks WHERE click_id=?",
                      (click_id,)).fetchone()

    if row:
        completions, keys_issued = row
    else:
        completions, keys_issued = 0, 0

    completions += 1

    # Already issued after 2 completions — don't issue again
    if completions >= REQUIRED_COMPLETIONS and keys_issued >= 1:
        con.execute("UPDATE postbacks SET last_ip=?, last_ts=? WHERE click_id=?",
                    (ip, int(time.time()), click_id))
        con.commit()
        con.close()
        return "already_issued", 200

    # 2 completions — issue key
    if completions >= REQUIRED_COMPLETIONS:
        suffix = secrets.token_hex(3).upper()
        key = f"BAZA_BCL_{suffix}"
        expires = int(time.time()) + 24 * 3600
        cfg = PLAN_CONFIG["free"]

        con.execute("INSERT INTO keys VALUES (?,?,?,?,?,?,?,?)",
                    (key, "free", expires, "[]", cfg["tokens"], cfg["tokens"], 0, int(time.time())))

        con.execute("""INSERT INTO postbacks (click_id, completions, last_ip, last_ts, keys_issued)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(click_id) DO UPDATE SET
                       completions=excluded.completions,
                       last_ip=excluded.last_ip,
                       last_ts=excluded.last_ts,
                       keys_issued=excluded.keys_issued""",
                    (click_id, completions, ip, int(time.time()), 1))
        con.commit()
        con.close()

        print(f"[Postback] click_id={click_id} → {completions}/{REQUIRED_COMPLETIONS} → KEY={key}")
        return key, 200

    # First completion — record, do NOT issue
    con.execute("""INSERT INTO postbacks (click_id, completions, last_ip, last_ts, keys_issued)
                   VALUES (?,?,?,?,0)
                   ON CONFLICT(click_id) DO UPDATE SET
                   completions=excluded.completions,
                   last_ip=excluded.last_ip,
                   last_ts=excluded.last_ts""",
                (click_id, completions, ip, int(time.time())))
    con.commit()
    con.close()

    print(f"[Postback] click_id={click_id} → {completions}/{REQUIRED_COMPLETIONS} (waiting)")
    return f"registered {completions}/{REQUIRED_COMPLETIONS}", 200

# ============================================================
# STARTUP
# ============================================================
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

