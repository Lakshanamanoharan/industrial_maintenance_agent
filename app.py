import json
import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# ==============================
# BASE DIRECTORY (VERY IMPORTANT)
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute paths
RULES_PATH = os.path.join(BASE_DIR, "rules", "rules.json")
DB_FOLDER = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_FOLDER, "maintenance.db")

# ==============================
# LOAD RULES
# ==============================
with open(RULES_PATH) as f:
    rules_priority = json.load(f)

# ==============================
# DATABASE INITIALIZATION
# ==============================
def init_db():
    os.makedirs(DB_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vibration INTEGER,
            temperature INTEGER,
            usage_hours INTEGER,
            last_service INTEGER,
            power_fluctuation TEXT,
            noise INTEGER,
            sensor_error TEXT,
            oil_level_low TEXT,
            condition TEXT,
            action TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ==============================
# INFERENCE ENGINE
# ==============================
def infer_condition(data):
    for rule in rules_priority:
        try:
            if eval(rule["condition"], {"__builtins__": None}, data):
                return rule["status"], rule["action"]
        except Exception as e:
            print("Rule evaluation error:", e)

    return "Unknown", "No action defined"


# ==============================
# HOME PAGE
# ==============================
@app.route("/", methods=["GET", "POST"])
def index():
    condition = None
    action = None

    if request.method == "POST":
        data = {
            "vibration": int(request.form["vibration"]),
            "temperature": int(request.form["temperature"]),
            "usage_hours": int(request.form["usage_hours"]),
            "last_service": int(request.form["last_service"]),
            "power_fluctuation": request.form.get("power_fluctuation") == "yes",
            "noise": int(request.form["noise"]),
            "sensor_error": request.form.get("sensor_error") == "yes",
            "oil_level_low": request.form.get("oil_level_low") == "yes"
        }

        condition, action = infer_condition(data)

        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO history (
                vibration, temperature, usage_hours, last_service,
                power_fluctuation, noise, sensor_error, oil_level_low,
                condition, action
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["vibration"],
            data["temperature"],
            data["usage_hours"],
            data["last_service"],
            str(data["power_fluctuation"]),
            data["noise"],
            str(data["sensor_error"]),
            str(data["oil_level_low"]),
            condition,
            action
        ))

        conn.commit()
        conn.close()

    return render_template("index.html", condition=condition, action=action)


# ==============================
# HISTORY PAGE
# ==============================
@app.route("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM history ORDER BY id DESC")
    records = cur.fetchall()

    conn.close()

    return render_template("history.html", records=records)


# ==============================
# CLEAR HISTORY
# ==============================
@app.route("/clear")
def clear_history():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM history")

    conn.commit()
    conn.close()

    return redirect(url_for("history"))


# ==============================
# RUN LOCALLY
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
