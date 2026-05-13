from supabase import create_client
from flask import Flask, render_template, request, redirect
import json

SUPABASE_URL = "https://rtjunmrzthconkmrrxkg.supabase.co"
SUPABASE_KEY = "sb_publishable_IBCPN_sCgzUkcwcRRiLL_w_1o5Rrw3m"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

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

    # Sammlung
    collection = {
        row["number"]: row["count"]
        for row in rows
    }

    incoming = set()
    outgoing = {}

    for t in trades:

        # Incoming
        receive = [
            x.strip()
            for x in t["receive_stickers"].split(",")
        ]

        for r in receive:
            incoming.add(r)

        # Outgoing
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
        outgoing=outgoing
    )


@app.route("/add", methods=["POST"])
def add():

    sticker = request.form["sticker"]

    existing = supabase.table("stickers") \
        .select("*") \
        .eq("number", sticker) \
        .execute()

    if existing.data:

        count = existing.data[0]["count"] + 1

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

    return redirect("/")


@app.route("/trade", methods=["POST"])
def trade():

    give = request.form["give"]
    receive = request.form["receive"]

    give_list = [x.strip() for x in give.split(",")]

    # Prüfen ob Sticker doppelt
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

    return redirect("/")


@app.route("/delete_trade/<int:trade_id>")
def delete_trade(trade_id):

    supabase.table("trades") \
        .delete() \
        .eq("id", trade_id) \
        .execute()

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)