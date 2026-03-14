# Dehati-Connect 🌾📱

**SMS-based Skill & Labor Directory for Rural India**

> *"Gaon ke liye ek Offline LinkedIn"* — Connecting farmers with local skilled workers via simple SMS.

---

## Problem Statement

In rural villages, when a tractor breaks down, a wall needs to be built, or workers are needed
to harvest crops, people rely entirely on word-of-mouth.  There is no directory, no phonebook,
and smartphone internet is unreliable.

**Dehati-Connect** solves this by letting anyone send a plain SMS to find or register a
skilled worker — no smartphone, no internet, no app required.

---

## How It Works

```
Farmer sends SMS  ──►  Dehati-Connect Backend  ──►  SQLite DB
                               │
                               ▼
                     Top-3 workers returned
                     as SMS reply to farmer
```

### Search a Worker

```
NEED Tractor Mechanic Ramnagar
```

Reply:

```
🔧 Top 3 Tractor Mechanic near Ramnagar:

1. Ramesh Kumar (Tractor Mechanic)
   📍 Ramnagar
   📞 +919870001001
   ★★★★★ (3 jobs)

2. Suresh Yadav (Tractor Mechanic)
   📍 Ballia
   📞 +919870001002
   ★★★☆☆ (1 jobs)
```

### Register as a Worker

```
REGISTER Ram Lal Tractor Mechanic Ramnagar
```

Reply:

```
✅ Ram Lal, aapka registration ho gaya!
Skill: Tractor Mechanic
Location: Ramnagar
Aapko kaam milne par SMS aayega.
```

### Supported SMS Keywords

| Action   | English         | Hindi           |
|----------|-----------------|-----------------|
| Search   | `NEED`          | `CHAHIYE`, `DHUNDO`, `KHOJO` |
| Register | `REGISTER`      | `PANJIYAN`, `PANJIKARAN` |

### Supported Skills

| English         | Hindi Alias     |
|-----------------|-----------------|
| Tractor Mechanic | Tractor        |
| Mason           | Mistri, Diwaar  |
| Plumber         | —               |
| Electrician     | Bijli           |
| Labourer        | Mazdoor         |
| Harvesting      | Fasal           |
| Carpenter       | Barhai          |
| Painter         | Rangai          |
| Welder          | —               |
| Driver          | —               |
| Pump Operator   | Pump            |

---

## Tech Stack

| Layer    | Technology                     |
|----------|-------------------------------|
| Backend  | Python 3.10+ · Flask 3.x      |
| Database | SQLite (zero-config, embedded) |
| SMS Gate | Twilio (webhook-compatible)    |
| Parsing  | Custom keyword engine          |

---

## Project Structure

```
dehati-connect/
├── app.py          # Flask webhook — receives & replies to SMS
├── sms_parser.py   # Keyword parsing engine (REGISTER / SEARCH / UNKNOWN)
├── database.py     # SQLite helpers (CRUD + search)
├── schema.sql      # Database schema (workers, sms_log, ratings)
├── seed_data.py    # Load sample workers for demo
├── requirements.txt
└── tests/
    ├── test_sms_parser.py   # Unit tests for parser
    └── test_database.py     # Integration tests for DB layer
```

---

## Quick Start

```bash
# 1. Install dependencies
cd dehati-connect
pip install -r requirements.txt

# 2. Initialise DB and load sample data
python seed_data.py

# 3. Start the server
python app.py        # runs on http://localhost:5000

# 4. Run tests
pytest tests/ -v
```

### Endpoints

| Method | Path     | Description                          |
|--------|----------|--------------------------------------|
| POST   | `/sms`   | Twilio SMS webhook (From + Body)     |
| GET    | `/health`| Health check                         |
| GET    | `/stats` | Aggregated usage statistics          |

---

## SMS Gateway Integration (Twilio)

1. Buy a Twilio number (₹0 trial credit available).
2. In Twilio Console → Phone Numbers → Messaging → Webhook URL:
   ```
   https://<your-server>/sms
   ```
3. That's it — any SMS to your Twilio number is processed automatically.

---

## Impact

- 🌾 **Farmers** get instant access to skilled workers without leaving home.
- 🔧 **Workers** get more jobs and build a digital reputation (ratings).
- 📵 **No internet required** — works on the most basic feature phones.
- 🗂️ **Fully offline-capable** — SQLite needs no separate database server.
