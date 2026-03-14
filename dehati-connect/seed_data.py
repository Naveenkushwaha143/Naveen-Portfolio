"""
seed_data.py — Populate the database with sample workers for demo / testing.

Run once:
    python seed_data.py
"""

import database as db
from app import _build_skill_tags

WORKERS = [
    # Tractor mechanics
    {"name": "Ramesh Kumar",    "phone": "+919870001001", "location": "ramnagar",    "skill": "tractor mechanic"},
    {"name": "Suresh Yadav",    "phone": "+919870001002", "location": "ballia",      "skill": "tractor mechanic"},
    {"name": "Dinesh Prasad",   "phone": "+919870001003", "location": "gopalganj",   "skill": "tractor mechanic"},
    # Masons / Mistri
    {"name": "Manoj Mistri",    "phone": "+919870002001", "location": "ramnagar",    "skill": "mason"},
    {"name": "Birbal Thakur",   "phone": "+919870002002", "location": "vaishali",    "skill": "mason"},
    {"name": "Lala Ram",        "phone": "+919870002003", "location": "patna",       "skill": "mason"},
    # Plumbers
    {"name": "Vijay Plumber",   "phone": "+919870003001", "location": "patna",       "skill": "plumber"},
    {"name": "Arvind Kumar",    "phone": "+919870003002", "location": "muzaffarpur", "skill": "plumber"},
    # Electricians
    {"name": "Bijli Babu",      "phone": "+919870004001", "location": "siwan",       "skill": "electrician"},
    {"name": "Raju Electrician","phone": "+919870004002", "location": "ballia",      "skill": "electrician"},
    # Labourers
    {"name": "Chandan Mazdoor", "phone": "+919870005001", "location": "gopalganj",   "skill": "labourer"},
    {"name": "Santosh Singh",   "phone": "+919870005002", "location": "ramnagar",    "skill": "labourer"},
    {"name": "Hari Prasad",     "phone": "+919870005003", "location": "vaishali",    "skill": "labourer"},
    # Carpenters
    {"name": "Kapil Barhai",    "phone": "+919870006001", "location": "patna",       "skill": "carpenter"},
    {"name": "Sanjay Carpenter","phone": "+919870006002", "location": "muzaffarpur", "skill": "carpenter"},
    # Drivers
    {"name": "Guddu Driver",    "phone": "+919870007001", "location": "gopalganj",   "skill": "driver"},
    {"name": "Rahul Chauffeur", "phone": "+919870007002", "location": "patna",       "skill": "driver"},
    # Harvesters
    {"name": "Mohan Kaatne",    "phone": "+919870008001", "location": "siwan",       "skill": "harvesting"},
    {"name": "Raman Fasal",     "phone": "+919870008002", "location": "gopalganj",   "skill": "harvesting"},
    # Welders
    {"name": "Iron Babu",       "phone": "+919870009001", "location": "ballia",      "skill": "welder"},
]


def seed():
    db.init_db()
    inserted = 0
    for w in WORKERS:
        tags = _build_skill_tags(w["skill"])
        row_id = db.register_worker(
            name=w["name"],
            phone=w["phone"],
            location=w["location"],
            skill=w["skill"],
            skill_tags=tags,
        )
        if row_id:
            inserted += 1

    # Give a few workers some jobs + ratings so the ranking is non-trivial
    ratings = [
        ("+919870001001", 5), ("+919870001001", 4), ("+919870001001", 5),
        ("+919870001002", 3), ("+919870002001", 5), ("+919870002001", 5),
        ("+919870003001", 4), ("+919870004001", 5), ("+919870005001", 3),
    ]
    # Look up worker ids first (read-only connection), then apply ratings one at a time
    worker_ids = {}
    with db.get_db() as conn:
        for phone, _ in ratings:
            if phone not in worker_ids:
                row = conn.execute("SELECT id FROM workers WHERE phone=?", (phone,)).fetchone()
                if row:
                    worker_ids[phone] = row["id"]

    for phone, stars in ratings:
        if phone in worker_ids:
            db.add_rating(worker_ids[phone], "+910000000000", stars)
            with db.get_db() as conn:
                conn.execute("UPDATE workers SET jobs_done = jobs_done + 1 WHERE id=?",
                             (worker_ids[phone],))

    print(f"Seeded {inserted} new workers (skipped duplicates).")


if __name__ == "__main__":
    seed()
