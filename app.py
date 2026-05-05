from flask import Flask, render_template, request, redirect
import sqlite3

RESET_PASSWORD = "0408"

app = Flask(__name__)

MAX_STICKER = 920  # anpassen!

def get_db():
    return sqlite3.connect("stickers.db")

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS stickers (
            number TEXT PRIMARY KEY,
            count INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Dummy Sticker-Daten (später erweiterbar)
STICKER_INFO = {
    "1": {"team": "Deutschland", "name": "Spieler 1"},
    "2": {"team": "Deutschland", "name": "Spieler 2"},
    "3": {"team": "Frankreich", "name": "Spieler 3"},
}

@app.route("/")
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM stickers")
    rows = c.fetchall()
    conn.close()

    data = {n: c for n, c in rows}

    table = []

    for i in range(1, MAX_STICKER + 1):
        num = str(i)
        count = data.get(num, 0)

        if count == 0:
            color = "red"
        elif count == 1:
            color = "green"
        else:
            color = "yellow"

        info = STICKER_INFO.get(num, {"team": "Unbekannt", "name": "-"})

        table.append({
            "num": num,
            "count": count,
            "color": color,
            "team": info["team"],
            "name": info["name"]
        })

    return render_template("index.html", table=table)

@app.route("/add", methods=["POST"])
def add():
    nums = request.form["stickers"].split(",")

    conn = get_db()
    c = conn.cursor()

    for n in nums:
        n = n.strip()

        if not n.isdigit():
            continue

        if int(n) < 1 or int(n) > MAX_STICKER:
            continue

        c.execute("SELECT count FROM stickers WHERE number=?", (n,))
        row = c.fetchone()

        if row:
            c.execute("UPDATE stickers SET count=? WHERE number=?", (row[0]+1, n))
        else:
            c.execute("INSERT INTO stickers VALUES (?,?)", (n, 1))

    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    num = request.form["num"]

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM stickers WHERE number=?", (num,))
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/reset", methods=["POST"])
def reset():
    password = request.form.get("password")

    if password != RESET_PASSWORD:
        return "❌ Falsches Passwort!"

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM stickers")
    conn.commit()
    conn.close()

    return redirect("/")

app.run(host="0.0.0.0", port=10000)