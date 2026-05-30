import sqlite3
import os
from datetime import datetime
from typing import Optional


DB_PATH = "sales_agent.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_leads INTEGER DEFAULT 0,
            researched INTEGER DEFAULT 0,
            qualified INTEGER DEFAULT 0,
            validated INTEGER DEFAULT 0,
            sent INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds REAL,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id INTEGER REFERENCES pipelines(id),
            company_name TEXT NOT NULL,
            website TEXT,
            phone TEXT,
            email TEXT,
            contact_person TEXT,
            position TEXT,
            industry TEXT,
            company_size TEXT,
            location TEXT,
            source TEXT,
            source_primary TEXT,
            score INTEGER DEFAULT 0,
            score_breakdown TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            validation_status TEXT,
            validation_details TEXT,
            research_data TEXT,
            email_draft TEXT,
            email_subject TEXT,
            email_edited TEXT,
            email_edited_subject TEXT,
            checked INTEGER DEFAULT 0,
            sent_at TIMESTAMP,
            send_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id INTEGER REFERENCES pipelines(id),
            lead_id INTEGER REFERENCES leads(id),
            agent_name TEXT NOT NULL,
            action TEXT,
            input_data TEXT,
            output_data TEXT,
            tokens_used INTEGER,
            cost REAL,
            duration_ms INTEGER,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_leads_pipeline ON leads(pipeline_id);
        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score);
        CREATE INDEX IF NOT EXISTS idx_logs_pipeline ON agent_logs(pipeline_id);
    """)

    conn.commit()
    conn.close()


def create_pipeline(query: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pipelines (query, status, started_at) VALUES (?, ?, ?)",
        (query, "running", datetime.utcnow().isoformat()),
    )
    pipeline_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pipeline_id


def update_pipeline(pipeline_id: int, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    cursor.execute(
        f"UPDATE pipelines SET {sets} WHERE id = ?", (*vals, pipeline_id)
    )
    conn.commit()
    conn.close()


def insert_lead(pipeline_id: int, data: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    cursor.execute(
        f"INSERT INTO leads ({cols}) VALUES ({placeholders})",
        list(data.values()),
    )
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def update_lead(lead_id: int, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    cursor.execute(f"UPDATE leads SET {sets} WHERE id = ?", (*vals, lead_id))
    conn.commit()
    conn.close()


def get_leads(
    pipeline_id: Optional[int] = None,
    status: Optional[str] = None,
    min_score: int = 0,
    max_score: int = 100,
    industry: Optional[str] = None,
    source: Optional[str] = None,
    validation_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    conditions = []
    params = []
    if pipeline_id:
        conditions.append("l.pipeline_id = ?")
        params.append(pipeline_id)
    if status:
        conditions.append("l.status = ?")
        params.append(status)
    if min_score > 0:
        conditions.append("l.score >= ?")
        params.append(min_score)
    if max_score < 100:
        conditions.append("l.score <= ?")
        params.append(max_score)
    if industry:
        conditions.append("l.industry = ?")
        params.append(industry)
    if source:
        conditions.append("l.source = ?")
        params.append(source)
    if validation_status:
        conditions.append("l.validation_status = ?")
        params.append(validation_status)
    if search:
        conditions.append("(l.company_name LIKE ? OR l.contact_person LIKE ? OR l.email LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    where = " AND ".join(conditions) if conditions else "1=1"
    cursor.execute(
        f"""SELECT l.*, p.query as pipeline_query
            FROM leads l
            LEFT JOIN pipelines p ON l.pipeline_id = p.id
            WHERE {where}
            ORDER BY l.score DESC, l.created_at DESC
            LIMIT ? OFFSET ?""",
        (*params, limit, offset),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def count_leads(**filters) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    conditions = []
    params = []
    for key, val in filters.items():
        if val is not None:
            conditions.append(f"{key} = ?")
            params.append(val)
    where = " AND ".join(conditions) if conditions else "1=1"
    cursor.execute(f"SELECT COUNT(*) as cnt FROM leads WHERE {where}", params)
    count = cursor.fetchone()["cnt"]
    conn.close()
    return count


def get_pipeline_stats(pipeline_id: Optional[int] = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    if pipeline_id:
        cursor.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,))
        pipeline = dict(cursor.fetchone() or {})
    else:
        cursor.execute(
            "SELECT * FROM pipelines ORDER BY id DESC LIMIT 1"
        )
        pipeline = dict(cursor.fetchone() or {})
    conn.close()
    return pipeline


def get_dashboard_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(*) as c FROM leads")
    stats["total_leads"] = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE status = 'research_complete'")
    stats["researched"] = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE score >= 75")
    stats["qualified_75"] = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE validation_status = 'passed'")
    stats["validated"] = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE checked = 1")
    stats["checked"] = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE status = 'sent'")
    stats["sent"] = cursor.fetchone()["c"]
    cursor.execute("SELECT * FROM pipelines ORDER BY id DESC LIMIT 1")
    p = cursor.fetchone()
    if p:
        stats["last_run_at"] = p["started_at"]
        stats["last_run_status"] = p["status"]
    else:
        stats["last_run_at"] = None
        stats["last_run_status"] = None
    conn.close()
    return stats


def lead_exists(email: str = "", company: str = "") -> bool:
    # Only match on fields that are actually provided. Matching on an empty
    # string used to flag every contact-less lead as a duplicate, which silently
    # dropped brand-new leads from the pipeline.
    conditions = []
    params = []
    if email:
        conditions.append("email = ?")
        params.append(email)
    if company:
        conditions.append("company_name = ?")
        params.append(company)
    if not conditions:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT COUNT(*) as c FROM leads WHERE {' OR '.join(conditions)}",
        params,
    )
    count = cursor.fetchone()["c"] > 0
    conn.close()
    return count


def get_lead_by_id(lead_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_distinct_industries() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND industry != ''"
    )
    rows = [r["industry"] for r in cursor.fetchall()]
    conn.close()
    return rows


def get_distinct_sources() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT source FROM leads WHERE source IS NOT NULL AND source != ''"
    )
    rows = [r["source"] for r in cursor.fetchall()]
    conn.close()
    return rows
