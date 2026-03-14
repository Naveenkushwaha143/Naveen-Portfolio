"""
app.py — Flask web-hook for Dehati-Connect.

Incoming SMS arrives via a POST to /sms (Twilio-compatible format).
The app parses the message, queries the SQLite database, and returns
a TwiML (or plain-text) reply that the SMS gateway sends back to the
caller.

Usage:
    pip install -r requirements.txt
    python app.py            # development server on port 5000

Environment variables:
    DEHATI_DB   Path to the SQLite database file (default: dehati_connect.db)
    PORT        HTTP port (default: 5000)
"""

import os
from flask import Flask, Response, request

import database as db
from sms_parser import SKILL_ALIASES, parse_sms

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

db.init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USAGE_HINT = (
    "Dehati-Connect:\n"
    "  Search : NEED <Skill> [Location]\n"
    "  Register: REGISTER <Name> <Skill> <Location>\n"
    "  Example : NEED Tractor Mechanic Ramnagar"
)


def _twiml_reply(message: str) -> Response:
    """Wrap a plain-text message in a minimal TwiML envelope."""
    body = f"<?xml version='1.0' encoding='UTF-8'?><Response><Message>{message}</Message></Response>"
    return Response(body, mimetype="text/xml")


def _format_worker(worker, rank: int) -> str:
    stars = "★" * round(worker["rating"]) + "☆" * (5 - round(worker["rating"]))
    return (
        f"{rank}. {worker['name']} ({worker['skill'].title()})\n"
        f"   📍 {worker['location'].title()}\n"
        f"   📞 {worker['phone']}\n"
        f"   {stars} ({worker['jobs_done']} jobs)"
    )


# ---------------------------------------------------------------------------
# SMS webhook
# ---------------------------------------------------------------------------

@app.route("/sms", methods=["POST"])
def sms_webhook():
    """
    Handle an incoming SMS from the gateway.

    Expected POST params (Twilio-style):
        From  — sender's phone number
        Body  — SMS text
    """
    sender = request.form.get("From", "").strip()
    body   = request.form.get("Body", "").strip()

    if not body:
        return _twiml_reply(USAGE_HINT)

    db.log_sms("IN", sender, body)
    parsed = parse_sms(body, sender)

    # ---- REGISTER --------------------------------------------------------
    if parsed.intent == "REGISTER":
        if not parsed.is_valid:
            reply = "❌ " + "\n".join(parsed.errors)
        else:
            # Build comma-separated skill tags from the canonical skill
            skill_tags = _build_skill_tags(parsed.skill)
            row_id = db.register_worker(
                name=parsed.name,
                phone=sender or "unknown",
                location=parsed.location,
                skill=parsed.skill,
                skill_tags=skill_tags,
            )
            if row_id:
                reply = (
                    f"✅ {parsed.name}, aapka registration ho gaya!\n"
                    f"Skill: {parsed.skill.title()}\n"
                    f"Location: {parsed.location.title()}\n"
                    "Aapko kaam milne par SMS aayega."
                )
            else:
                reply = (
                    "⚠️ Yeh number pahle se registered hai.\n"
                    "Agar kuch badalna hai to humse sampark karein."
                )

    # ---- SEARCH ----------------------------------------------------------
    elif parsed.intent == "SEARCH":
        if not parsed.is_valid:
            reply = "❌ " + "\n".join(parsed.errors)
        else:
            workers = db.search_workers(
                keyword=parsed.skill,
                location=parsed.location,
                limit=3,
            )
            if workers:
                lines = [f"🔧 Top {len(workers)} {parsed.skill.title()} near {(parsed.location or 'aapke area').title()}:\n"]
                lines += [_format_worker(w, i + 1) for i, w in enumerate(workers)]
                reply = "\n".join(lines)
            else:
                reply = (
                    f"😔 Abhi {parsed.skill.title()} available nahi hai"
                    + (f" {parsed.location.title()} mein" if parsed.location else "")
                    + ".\nThodi der baad try karein ya REGISTER karke apna naam add karein."
                )

    # ---- UNKNOWN ---------------------------------------------------------
    else:
        reply = USAGE_HINT

    db.log_sms("OUT", sender, reply, intent=parsed.intent)
    return _twiml_reply(reply)


# ---------------------------------------------------------------------------
# Simple health-check and stats endpoints
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return {"status": "ok", "service": "Dehati-Connect"}


@app.route("/stats")
def stats():
    """Return summary stats (no personal data exposed)."""
    with db.get_db() as conn:
        total_workers  = conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
        avail_workers  = conn.execute("SELECT COUNT(*) FROM workers WHERE available=1").fetchone()[0]
        total_searches = conn.execute("SELECT COUNT(*) FROM sms_log WHERE intent='SEARCH'").fetchone()[0]
        total_reg      = conn.execute("SELECT COUNT(*) FROM sms_log WHERE intent='REGISTER'").fetchone()[0]
    return {
        "total_workers":   total_workers,
        "available_now":   avail_workers,
        "total_searches":  total_searches,
        "total_registers": total_reg,
    }


# ---------------------------------------------------------------------------
# Skill-tag builder
# ---------------------------------------------------------------------------

def _build_skill_tags(canonical_skill: str) -> str:
    """
    Return a comma-separated string of all aliases that map to *canonical_skill*.
    This allows the LIKE search to hit any alias a caller might type.
    """
    tags = {canonical_skill}
    for alias, canon in SKILL_ALIASES.items():
        if canon == canonical_skill:
            tags.add(alias)
    return ",".join(sorted(tags))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
