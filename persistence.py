import json
import sqlite3
from pathlib import Path
from job import Job, JobStatus

DB_PATH = Path("jobs.db")

SCHEMA = """

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    func_name TEXT NOT NULL,
    args TEXT NOT NULL,
    kwargs TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dead_letter (
    id TEXT PRIMARY KEY,
    func_name TEXT NOT NULL,
    args TEXT NOT NULL,
    kwargs TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    failed_at TEXT NOT NULL
);

"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def save_job(conn: sqlite3.Connection, job: Job) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO jobs
           (id, func_name, args, kwargs, status, attempts, max_attempts, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job.id, job.func_name, json.dumps(job.args), json.dumps(job.kwargs),
            job.status.value, job.attempts, job.max_attempts, job.created_at.isoformat(),
        ),
    )
    conn.commit()


def fetch_next_pending(conn: sqlite3.Connection) -> Job | None:
    """Atomically claim the next pending job."""
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY created_at LIMIT 1",
        (JobStatus.PENDING.value,),
    ).fetchone()
    if row is None:
        conn.commit()
        return None

    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (JobStatus.RUNNING.value, row[0]))
    conn.commit()

    return Job(
        id=row[0], func_name=row[1], args=tuple(json.loads(row[2])),
        kwargs=json.loads(row[3]), status=JobStatus.RUNNING,
        attempts=row[5], max_attempts=row[6],
    )