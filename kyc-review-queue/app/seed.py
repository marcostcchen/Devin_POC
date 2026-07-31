"""Deterministic synthetic seed data.

Everything here is fabricated: invented names, `SYNTH-` prefixed document numbers and
placeholder filenames. Risk levels are pre-assigned labels, not the output of any
screening. No real customer data, and no real-looking identifiers (no SSNs, no
addresses), belongs in this file.
"""

import random
from datetime import datetime, timedelta, timezone

CASE_COUNT = 18

# Invented surname-ish and given-name-ish tokens, combined below into obviously
# fictional personas.
GIVEN_NAMES = [
    "Ilva", "Toren", "Maible", "Osric", "Brenna", "Kadeem", "Sunni", "Ferrin",
    "Odalys", "Wrenley", "Tavish", "Neris", "Corvin", "Lumi", "Basten", "Yevka",
    "Renzo", "Althea",
]
FAMILY_NAMES = [
    "Quilty", "Vandermeer", "Okonkwo-Reyes", "Fenwick", "Sallowby", "Ntembi",
    "Halvard", "Dresque", "Marchetti", "Oyelaran", "Bricklow", "Sundqvist",
    "Achterberg", "Perrault", "Nakamura-Vale", "Ferrante", "Ozdemir", "Kingsholm",
]
JURISDICTIONS = ["Northmark", "Vaduzia", "Port Ashen", "Cardova", "Estrella Isles", "Kelvara"]
RISK_LEVELS = ["low", "low", "low", "medium", "medium", "high"]
RISK_NOTES = {
    "low": [
        "mock screening: no adverse media hits",
        "mock screening: document quality good, no flags",
    ],
    "medium": [
        "mock screening: name similarity to an unrelated watchlist entry",
        "mock screening: address history incomplete",
        "mock screening: expected transaction volume above segment average",
    ],
    "high": [
        "mock screening: possible PEP association (label only, not verified)",
        "mock screening: high-risk jurisdiction + shell-company ownership pattern",
    ],
}
STATUSES = ["new", "new", "new", "new", "in_review", "escalated"]
DOC_TYPES = [
    ("passport", "passport_scan.pdf"),
    ("proof_of_address", "utility_statement.pdf"),
    ("selfie_liveness", "liveness_capture.jpg"),
    ("company_registry", "registry_extract.pdf"),
    ("source_of_funds", "funds_declaration.pdf"),
]


def build_cases(now: datetime) -> list[dict]:
    """Build CASE_COUNT synthetic cases. Seeded RNG keeps the queue reproducible."""
    rng = random.Random(20240517)
    cases = []
    for i in range(CASE_COUNT):
        risk = RISK_LEVELS[i % len(RISK_LEVELS)]
        status = STATUSES[(i * 5) % len(STATUSES)]
        submitted = now - timedelta(hours=rng.randint(2, 240))
        name = f"{rng.choice(GIVEN_NAMES)} {rng.choice(FAMILY_NAMES)}"
        documents = [DOC_TYPES[0], DOC_TYPES[1]]
        if risk != "low":
            documents.append(DOC_TYPES[2])
        if risk == "high":
            documents.extend([DOC_TYPES[3], DOC_TYPES[4]])
        cases.append(
            {
                "reference": f"KYC-2199-{i + 1:03d}",
                "customer_name": name,
                "customer_ref": f"SYNTH-CUST-{4000 + i * 7}",
                "document_number": f"SYNTH-DOC-{rng.randint(10000, 99999)}",
                "jurisdiction": rng.choice(JURISDICTIONS),
                "risk_level": risk,
                "risk_note": rng.choice(RISK_NOTES[risk]),
                "status": status,
                "submitted_at": submitted.isoformat(timespec="seconds"),
                "documents": [
                    {
                        "doc_type": doc_type,
                        "filename": f"{f'SYNTH-CUST-{4000 + i * 7}'}_{filename}",
                        "received_at": (submitted + timedelta(minutes=idx * 3)).isoformat(timespec="seconds"),
                    }
                    for idx, (doc_type, filename) in enumerate(documents)
                ],
            }
        )
    return cases


def seed(connect) -> None:
    conn = connect()
    try:
        if conn.execute("SELECT COUNT(*) AS c FROM cases").fetchone()["c"]:
            return
        now = datetime.now(timezone.utc)
        ts = now.isoformat(timespec="seconds")
        for case in build_cases(now):
            cur = conn.execute(
                "INSERT INTO cases (reference, customer_name, customer_ref, document_number,"
                " jurisdiction, risk_level, risk_note, status, outcome, submitted_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)",
                (
                    case["reference"],
                    case["customer_name"],
                    case["customer_ref"],
                    case["document_number"],
                    case["jurisdiction"],
                    case["risk_level"],
                    case["risk_note"],
                    case["status"],
                    case["submitted_at"],
                    ts,
                ),
            )
            case_id = int(cur.lastrowid)
            conn.executemany(
                "INSERT INTO case_documents (case_id, doc_type, filename, received_at) VALUES (?, ?, ?, ?)",
                [(case_id, d["doc_type"], d["filename"], d["received_at"]) for d in case["documents"]],
            )
            conn.execute(
                "INSERT INTO case_events (case_id, case_reference, actor, actor_role, action, reason,"
                " created_at) VALUES (?, ?, 'system', 'system', 'submitted', ?, ?)",
                (case_id, case["reference"], case["risk_note"], case["submitted_at"]),
            )
            if case["status"] in ("in_review", "escalated"):
                conn.execute(
                    "INSERT INTO case_events (case_id, case_reference, actor, actor_role, action, reason,"
                    " created_at) VALUES (?, ?, 'system', 'system', ?, ?, ?)",
                    (
                        case_id,
                        case["reference"],
                        case["status"],
                        "pre-existing state in seed data",
                        case["submitted_at"],
                    ),
                )
        conn.commit()
    finally:
        conn.close()
