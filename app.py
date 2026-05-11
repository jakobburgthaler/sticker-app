from flask import Flask, render_template, request, redirect
import sqlite3

import json

with open("sticker_data.json", "r", encoding="utf-8") as f:
    STICKER_DATA = json.load(f)

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

    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            give TEXT,
            receive TEXT,
            status TEXT
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

    c.execute("SELECT * FROM trades WHERE status='pending'")
    trades = c.fetchall()

    conn.close()

    collection = {n: c for n, c in rows}

    return render_template(
        "index.html",
        collection=collection,
        trades=trades,
        sticker_data=STICKER_DATA
    )

@app.route("/add", methods=["POST"])
def add():

    team = request.form["team"]
    number = request.form["number"]

    sticker = f"{team}{number}"

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT count FROM stickers WHERE number=?", (sticker,))
    row = c.fetchone()

    if row:
        c.execute(
            "UPDATE stickers SET count=? WHERE number=?",
            (row[0] + 1, sticker)
        )
    else:
        c.execute(
            "INSERT INTO stickers VALUES (?,?)",
            (sticker, 1)
        )

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

@app.route("/trade", methods=["POST"])
def trade():
    give = request.form["give"]
    receive = request.form["receive"]

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO trades (give, receive, status) VALUES (?, ?, ?)",
        (give, receive, "pending")
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/confirm_trade/<int:trade_id>")
def confirm_trade(trade_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT give, receive FROM trades WHERE id=?", (trade_id,))
    trade = c.fetchone()

    give = [x.strip() for x in trade[0].split(",")]
    receive = [x.strip() for x in trade[1].split(",")]

    # Prüfen
    for n in give:
        c.execute("SELECT count FROM stickers WHERE number=?", (n,))
        row = c.fetchone()
        if not row or row[0] <= 1:
            return f"❌ {n} nicht doppelt!"

    # Abziehen
    for n in give:
        c.execute("UPDATE stickers SET count=count-1 WHERE number=?", (n,))

    # Hinzufügen
    for n in receive:
        c.execute("SELECT count FROM stickers WHERE number=?", (n,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE stickers SET count=count+1 WHERE number=?", (n,))
        else:
            c.execute("INSERT INTO stickers VALUES (?,?)", (n, 1))

    # Status ändern
    c.execute("UPDATE trades SET status='done' WHERE id=?", (trade_id,))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete_trade/<int:trade_id>")
def delete_trade(trade_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM trades WHERE id=?", (trade_id,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)