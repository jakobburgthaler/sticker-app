from flask import Flask, render_template, request, redirect
import sqlite3

RESET_PASSWORD = "0408"

app = Flask(__name__)

MAX_STICKER = 920  # anpassen!

conn = get_db()
c = conn.cursor()
c.execute("SELECT * FROM trades WHERE status='pending'")
trades = c.fetchall()
conn.close()

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
    team_filter = request.args.get("team")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM stickers")
    rows = c.fetchall()
    conn.close()

    data = {n: c for n, c in rows}

    table = []
    teams = set()

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
        teams.add(info["team"])

        if team_filter and info["team"] != team_filter:
            continue

        table.append({
            "num": num,
            "count": count,
            "color": color,
            "team": info["team"],
            "name": info["name"]
        })

    return render_template("index.html", table=table, teams=sorted(teams), selected_team=team_filter, trades=trades)

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

app.run(host="0.0.0.0", port=10000)