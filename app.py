from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("stickers.db")

# Datenbank erstellen
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

@app.route("/")
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM stickers")
    data = c.fetchall()
    conn.close()
    return render_template("index.html", data=data)

@app.route("/add", methods=["POST"])
def add():
    nums = request.form["stickers"].split(",")

    conn = get_db()
    c = conn.cursor()

    for n in nums:
        n = n.strip()
        c.execute("SELECT count FROM stickers WHERE number=?", (n,))
        row = c.fetchone()

        if row:
            c.execute("UPDATE stickers SET count=? WHERE number=?", (row[0]+1, n))
        else:
            c.execute("INSERT INTO stickers VALUES (?,?)", (n, 1))

    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/trade", methods=["POST"])
def trade():
    give = [x.strip() for x in request.form["give"].split(",")]
    receive = [x.strip() for x in request.form["receive"].split(",")]

    conn = get_db()
    c = conn.cursor()

    for n in give:
        c.execute("SELECT count FROM stickers WHERE number=?", (n,))
        row = c.fetchone()
        if not row or row[0] <= 1:
            return f"Fehler: {n} nicht doppelt!"

    for n in give:
        c.execute("UPDATE stickers SET count=count-1 WHERE number=?", (n,))

    for n in receive:
        c.execute("SELECT count FROM stickers WHERE number=?", (n,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE stickers SET count=count+1 WHERE number=?", (n,))
        else:
            c.execute("INSERT INTO stickers VALUES (?,?)", (n, 1))

    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/duplicates")
def duplicates():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT number, count FROM stickers WHERE count > 1")
    data = c.fetchall()
    conn.close()
    return render_template("duplicates.html", data=data)

app.run(host="0.0.0.0", port=10000)