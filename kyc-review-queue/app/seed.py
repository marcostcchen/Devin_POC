"""Synthetic seed data.

Everything here is fabricated: placeholder names from a fictional-character style
list, obviously-fake document numbers (`SYNTH-...`), and document filenames that
point at nothing. No real customer PII, and nothing shaped like a real SSN,
passport number, or address.
"""

from datetime import datetime, timedelta, timezone

# (customer_name, country, document_type, risk_level, status)
CASES = [
    ("Test Persona Alpha", "Testland", "passport", "high", "new"),
    ("Test Persona Bravo", "Exampleia", "national_id", "medium", "new"),
    ("Test Persona Charlie", "Sampleland", "drivers_licence", "low", "new"),
    ("Test Persona Delta", "Testland", "passport", "high", "in_review"),
    ("Test Persona Echo", "Fictionia", "national_id", "low", "new"),
    ("Test Persona Foxtrot", "Exampleia", "passport", "medium", "in_review"),
    ("Test Persona Golf", "Sampleland", "national_id", "low", "closed"),
    ("Test Persona Hotel", "Fictionia", "passport", "high", "escalated"),
    ("Test Persona India", "Testland", "drivers_licence", "medium", "new"),
    ("Test Persona Juliett", "Exampleia", "passport", "low", "new"),
    ("Test Persona Kilo", "Sampleland", "national_id", "high", "new"),
    ("Test Persona Lima", "Fictionia", "drivers_licence", "medium", "in_review"),
    ("Test Persona Mike", "Testland", "passport", "low", "new"),
    ("Test Persona November", "Exampleia", "national_id", "medium", "new"),
    ("Test Persona Oscar", "Sampleland", "passport", "high", "escalated"),
    ("Test Persona Papa", "Fictionia", "national_id", "low", "closed"),
    ("Test Persona Quebec", "Testland", "drivers_licence", "medium", "new"),
    ("Test Persona Romeo", "Exampleia", "passport", "high", "new"),
]

DOCUMENTS = {
    "passport": ["passport_scan.pdf", "selfie_liveness.jpg"],
    "national_id": ["national_id_front.png", "national_id_back.png", "selfie_liveness.jpg"],
    "drivers_licence": ["drivers_licence.pdf", "proof_of_address.pdf"],
}


def seed() -> None:
    from app.db import connect

    conn = connect()
    try:
        if conn.execute("SELECT COUNT(*) AS c FROM cases").fetchone()["c"]:
            return
        base = datetime.now(timezone.utc) - timedelta(days=len(CASES))
        rows = []
        for i, (name, country, doc_type, risk, status) in enumerate(CASES, start=1):
            ts = (base + timedelta(days=i, minutes=i * 7)).isoformat(timespec="seconds")
            rows.append(
                (
                    f"KYC-{1000 + i}",
                    name,
                    country,
                    doc_type,
                    f"SYNTH-{doc_type[:3].upper()}-{1000 + i}",
                    risk,
                    status,
                    "|".join(DOCUMENTS[doc_type]),
                    ts,
                    ts,
                )
            )
        conn.executemany(
            "INSERT INTO cases (reference, customer_name, country, document_type,"
            " document_number, risk_level, status, documents, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
