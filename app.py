import json
import os

from flask import Flask, render_template, request, redirect, session
from supabase import create_client

# ============================================================
# KONFIGURATION
# ============================================================

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://rtjunmrzthconkmrrxkg.supabase.co"
)

SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_KEY fehlt. Bitte in Render unter Environment "
        "als Environment Variable hinterlegen."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")

RESET_PASSWORD = os.environ.get("RESET_PASSWORD", "0408")


# ============================================================
# STICKERDATEN LADEN
# ============================================================

with open("sticker_data.json", "r", encoding="utf-8") as f:
    STICKER_DATA = json.load(f)


def all_sticker_ids():
    """Gibt alle gültigen Sticker-IDs aus sticker_data.json zurück."""
    result = []

    for team in STICKER_DATA.values():
        result.extend(team.get("stickers", []))

    return set(result)


VALID_STICKERS = all_sticker_ids()


def split_stickers(value):
    """Kommagetrennte Stickerliste sauber in eine Liste umwandeln."""
    return [
        item.strip().upper()
        for item in (value or "").split(",")
        if item.strip()
    ]


def get_sticker_count(sticker):
    """Aktuellen Bestand eines Stickers aus Supabase lesen."""
    result = (
        supabase.table("stickers")
        .select("count")
        .eq("number", sticker)
        .execute()
    )

    if not result.data:
        return 0

    return result.data[0]["count"] or 0


def add_one_sticker(sticker):
    """Einen Sticker hinzufügen."""
    current = get_sticker_count(sticker)

    if current == 0:
        (
            supabase.table("stickers")
            .insert({"number": sticker, "count": 1})
            .execute()
        )
    else:
        (
            supabase.table("stickers")
            .update({"count": current + 1})
            .eq("number", sticker)
            .execute()
        )

    return current


def remove_one_sticker(sticker):
    """Einen Sticker aus der Sammlung entfernen."""
    current = get_sticker_count(sticker)

    if current <= 0:
        return False

    if current == 1:
        (
            supabase.table("stickers")
            .delete()
            .eq("number", sticker)
            .execute()
        )
    else:
        (
            supabase.table("stickers")
            .update({"count": current - 1})
            .eq("number", sticker)
            .execute()
        )

    return True


# ============================================================
# STARTSEITE
# ============================================================

@app.route("/")
def index():

    # Sammlung laden
    sticker_rows = (
        supabase.table("stickers")
        .select("*")
        .execute()
        .data
    )

    collection = {
        row["number"]: row["count"]
        for row in sticker_rows
    }

    # Offene Trades laden
    trades = (
        supabase.table("trades")
        .select("*")
        .eq("status", "pending")
        .order("id")
        .execute()
        .data
    )

    # Alle gültigen Sticker
    all_stickers = []

    for team in STICKER_DATA.values():
        all_stickers.extend(team.get("stickers", []))

    total_stickers = len(all_stickers)

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

    completion = round((owned / total_stickers) * 100) if total_stickers else 0

    # Sticker, die durch offene Trades hereinkommen
    incoming = set()

    # Sticker, die durch offene Trades abgegeben werden
    outgoing = {}

    for trade in trades:

        receive = split_stickers(trade.get("receive_stickers"))

        for sticker in receive:
            incoming.add(sticker)

        give = split_stickers(trade.get("give_stickers"))

        for sticker in give:
            outgoing[sticker] = outgoing.get(sticker, 0) + 1

    message = session.pop("message", None)

    return render_template(
        "index.html",
        collection=collection,
        trades=trades,
        sticker_data=STICKER_DATA,
        incoming=incoming,
        outgoing=outgoing,
        message=message,
        total_stickers=total_stickers,
        owned=owned,
        missing=missing,
        duplicates=duplicates,
        total_owned=total_owned,
        completion=completion
    )


# ============================================================
# STICKER HINZUFÜGEN
# ============================================================

@app.route("/add", methods=["POST"])
def add():

    team = request.form.get("team", "").strip().upper()
    number = request.form.get("number", "").strip()

    sticker = f"{team}{number}"

    if sticker not in VALID_STICKERS:
        session["message"] = f"❌ {sticker} ist kein gültiger Sticker."
        return redirect("/")

    old_count = add_one_sticker(sticker)

    if old_count == 0:
        session["message"] = f"🆕 {sticker} wurde neu hinzugefügt."
    else:
        session["message"] = (
            f"➕ {sticker} war bereits vorhanden "
            f"und ist jetzt {old_count + 1}× vorhanden."
        )

    return redirect("/")


# ============================================================
# EINEN STICKER ENTFERNEN
# ============================================================

@app.route("/delete_sticker", methods=["POST"])
def delete_sticker():

    sticker = request.form.get("sticker", "").strip().upper()

    if remove_one_sticker(sticker):
        session["message"] = f"🗑️ {sticker} wurde einmal entfernt."
    else:
        session["message"] = f"❌ {sticker} ist nicht in deiner Sammlung."

    return redirect("/")


# ============================================================
# TRADE ANLEGEN
# ============================================================

@app.route("/trade", methods=["POST"])
def trade():

    give = request.form.get("give", "")
    receive = request.form.get("receive", "")

    give_list = split_stickers(give)
    receive_list = split_stickers(receive)

    if not give_list or not receive_list:
        session["message"] = "❌ Bitte beide Seiten des Tauschs ausfüllen."
        return redirect("/")

    # Nur gültige Sticker zulassen
    invalid = [
        sticker
        for sticker in give_list + receive_list
        if sticker not in VALID_STICKERS
    ]

    if invalid:
        session["message"] = (
            "❌ Ungültige Sticker: " + ", ".join(sorted(set(invalid)))
        )
        return redirect("/")

    # Abzugebende Sticker müssen doppelt vorhanden sein
    for sticker in give_list:
        if get_sticker_count(sticker) <= 1:
            session["message"] = (
                f"❌ {sticker} ist nicht doppelt vorhanden "
                "und kann daher nicht abgegeben werden."
            )
            return redirect("/")

    (
        supabase.table("trades")
        .insert({
            "give_stickers": ", ".join(give_list),
            "receive_stickers": ", ".join(receive_list),
            "status": "pending"
        })
        .execute()
    )

    session["message"] = "🔄 Tausch gespeichert."
    return redirect("/")


# ============================================================
# TRADE BESTÄTIGEN
# ============================================================

@app.route("/confirm_trade/<int:trade_id>")
def confirm_trade(trade_id):

    result = (
        supabase.table("trades")
        .select("*")
        .eq("id", trade_id)
        .execute()
    )

    if not result.data:
        session["message"] = "❌ Trade nicht gefunden."
        return redirect("/")

    trade = result.data[0]

    if trade.get("status") != "pending":
        session["message"] = "❌ Dieser Trade ist nicht mehr offen."
        return redirect("/")

    give = split_stickers(trade.get("give_stickers"))
    receive = split_stickers(trade.get("receive_stickers"))

    # Vorher prüfen, damit der Trade nicht halb durchgeführt wird
    for sticker in give:
        if get_sticker_count(sticker) <= 1:
            session["message"] = (
                f"❌ {sticker} ist nicht mehr doppelt vorhanden. "
                "Der Trade wurde nicht durchgeführt."
            )
            return redirect("/")

    # Abgeben
    for sticker in give:
        remove_one_sticker(sticker)

    # Bekommen
    for sticker in receive:
        add_one_sticker(sticker)

    # Trade abschließen
    (
        supabase.table("trades")
        .update({"status": "done"})
        .eq("id", trade_id)
        .execute()
    )

    session["message"] = "✅ Tausch bestätigt."
    return redirect("/")


# ============================================================
# TRADE LÖSCHEN
# ============================================================

@app.route("/delete_trade/<int:trade_id>")
def delete_trade(trade_id):

    (
        supabase.table("trades")
        .delete()
        .eq("id", trade_id)
        .execute()
    )

    session["message"] = "🗑️ Tausch gelöscht."
    return redirect("/")


# ============================================================
# RESET
# ============================================================

@app.route("/reset", methods=["POST"])
def reset():

    password = request.form.get("password", "")

    if password != RESET_PASSWORD:
        session["message"] = "❌ Falsches Passwort."
        return redirect("/")

    (
        supabase.table("stickers")
        .delete()
        .neq("number", "")
        .execute()
    )

    (
        supabase.table("trades")
        .delete()
        .neq("id", 0)
        .execute()
    )

    session["message"] = "⚠️ Sammlung und Trades wurden zurückgesetzt."
    return redirect("/")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
