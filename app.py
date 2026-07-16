from supabase import create_client
from flask import Flask, render_template, request, redirect, session
import json

SUPABASE_URL = "https://rtjunmrzthconkmrrxkg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0anVubXJ6dGhjb25rbXJyeGtnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2OTgyMTEsImV4cCI6MjA5NDI3NDIxMX0.peGcjsdTm2cf2EKkK0OAoAoJouaxFvv4xMmPrSVithA"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "panini-manager-2026"

RESET_PASSWORD = "0408"

# Stickerdaten laden
with open("sticker_data.json", "r", encoding="utf-8") as f:
    STICKER_DATA = json.load(f)


@app.route("/")
def index():

    # Sticker laden
    rows = supabase.table("stickers").select("*").execute().data

    # Trades laden
    trades = supabase.table("trades") \
        .select("*") \
        .eq("status", "pending") \
        .execute().data

    print("################################")
    print(trades)
    print("################################")

    # Sammlung
    collection = {
        row["number"]: row["count"]
        for row in rows
    }


    # Statistik
    all_stickers = []

    for key, team in STICKER_DATA.items():
        all_stickers.extend(team["stickers"])

    TOTAL_STICKERS = len(all_stickers)

    owned = 0
    missing = 0
    duplicates = 0
    total_owned = 0

    for sticker in all_stickers:

        count = collection.get(sticker, 0)

        total_owned += count

        if count > 0:
            owned += 1
        else:
            missing += 1

        if count > 1:
            duplicates += count - 1

    completion = round((owned / TOTAL_STICKERS) * 100)

    # Incoming / Outgoing
    incoming = set()
    outgoing = {}

    for t in trades:

        # Sticker die reinkommen
        receive = [
            x.strip()
            for x in t["receive_stickers"].split(",")
        ]

        for r in receive:
            incoming.add(r)

        # Sticker die rausgehen
        give = [
            x.strip()
            for x in t["give_stickers"].split(",")
        ]

        for g in give:

            if g not in outgoing:
                outgoing[g] = 0

            outgoing[g] += 1

    return render_template(
        "index.html",
        collection=collection,
        trades=trades,
        sticker_data=STICKER_DATA,
        incoming=incoming,
        outgoing=outgoing,
        message=session.pop("message", None),
        total_stickers=TOTAL_STICKERS,
        owned=owned,
        missing=missing,
        duplicates=duplicates,
	total_owned=total_owned,
	completion=completion
    )


@app.route("/add", methods=["POST"])
def add():

    sticker = request.form["sticker"]

    existing = supabase.table("stickers") \
        .select("*") \
        .eq("number", sticker) \
        .execute()

    if existing.data:

        old_count = existing.data[0]["count"]
        count = old_count + 1

        if old_count == 1:
            session["message"] = f"🟡 {sticker} ist jetzt doppelt"
        else:
            session["message"] = f"🔴 {sticker} jetzt {count}x vorhanden"

        supabase.table("stickers") \
            .update({"count": count}) \
            .eq("number", sticker) \
            .execute()

    else:

        session["message"] = f"✅ {sticker} neu erhalten"

        supabase.table("stickers") \
            .insert({
                "number": sticker,
                "count": 1
            }) \
            .execute()

    return redirect("/")

@app.route("/remove", methods=["POST"])
def remove():

    sticker = request.form["sticker"]

    result = supabase.table("stickers") \
        .select("*") \
        .eq("number", sticker) \
        .execute()

    if not result.data:

        session["message"] = f"❌ {sticker} nicht vorhanden"

        return redirect("/")

    count = result.data[0]["count"]

    # Wenn nur 1x vorhanden → komplett löschen
    if count <= 1:

        supabase.table("stickers") \
            .delete() \
            .eq("number", sticker) \
            .execute()

        session["message"] = f"🗑️ {sticker} entfernt"

    else:

        new_count = count - 1

        supabase.table("stickers") \
            .update({"count": new_count}) \
            .eq("number", sticker) \
            .execute()

        session["message"] = f"➖ {sticker} reduziert auf {new_count}"

    return redirect("/")


@app.route("/delete", methods=["POST"])
def delete():

    num = request.form["num"]

    supabase.table("stickers") \
        .delete() \
        .eq("number", num) \
        .execute()

    return redirect("/")


@app.route("/reset", methods=["POST"])
def reset():

    password = request.form.get("password")

    if password != RESET_PASSWORD:
        return "❌ Falsches Passwort"

    supabase.table("stickers") \
        .delete() \
        .neq("number", "XXX") \
        .execute()

    supabase.table("trades") \
        .delete() \
        .neq("id", 0) \
        .execute()

    session["message"] = "⚠️ Sammlung wurde zurückgesetzt"

    return redirect("/")


@app.route("/trade", methods=["POST"])
def trade():

    give = request.form["give"]
    receive = request.form["receive"]

    give_list = [x.strip() for x in give.split(",")]

    # Prüfen ob Sticker doppelt vorhanden
    for sticker in give_list:

        result = supabase.table("stickers") \
            .select("*") \
            .eq("number", sticker) \
            .execute()

        if not result.data:
            return f"❌ {sticker} nicht vorhanden"

        if result.data[0]["count"] <= 1:
            return f"❌ {sticker} nicht doppelt vorhanden"

    # Trade speichern
    supabase.table("trades") \
        .insert({
            "give_stickers": give,
            "receive_stickers": receive,
            "status": "pending"
        }) \
        .execute()

    session["message"] = "🔄 Tausch gespeichert"

    return redirect("/")


@app.route("/confirm_trade/<int:trade_id>")
def confirm_trade(trade_id):

    result = supabase.table("trades") \
        .select("*") \
        .eq("id", trade_id) \
        .execute()

    if not result.data:
        return "❌ Trade nicht gefunden"

    trade = result.data[0]

    give = [
        x.strip()
        for x in trade["give_stickers"].split(",")
    ]

    receive = [
        x.strip()
        for x in trade["receive_stickers"].split(",")
    ]

    # Sticker abziehen
    for sticker in give:

        result = supabase.table("stickers") \
            .select("*") \
            .eq("number", sticker) \
            .execute()

        if not result.data:
            continue

        count = result.data[0]["count"] - 1

        supabase.table("stickers") \
            .update({"count": count}) \
            .eq("number", sticker) \
            .execute()

    # Sticker hinzufügen
    for sticker in receive:

        result = supabase.table("stickers") \
            .select("*") \
            .eq("number", sticker) \
            .execute()

        if result.data:

            count = result.data[0]["count"] + 1

            supabase.table("stickers") \
                .update({"count": count}) \
                .eq("number", sticker) \
                .execute()

        else:

            supabase.table("stickers") \
                .insert({
                    "number": sticker,
                    "count": 1
                }) \
                .execute()

    # Trade abschließen
    supabase.table("trades") \
        .update({"status": "done"}) \
        .eq("id", trade_id) \
        .execute()

    session["message"] = "✅ Tausch bestätigt"

    return redirect("/")


@app.route("/delete_trade/<int:trade_id>")
def delete_trade(trade_id):

    supabase.table("trades") \
        .delete() \
        .eq("id", trade_id) \
        .execute()

    session["message"] = "❌ Tausch gelöscht"

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)