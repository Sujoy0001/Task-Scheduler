"""Retry / backoff / dead-letter logic."""

import time
import json
from job import Job, JobStatus
from persistence import save_job


def handle_failure(conn, job: Job) -> None:
    job.attempts += 1

    if job.attempts < job.max_attempts:
        delay = 2 ** job.attempts   # 2s, 4s, 8s...
        print(f"Job {job.id} failed, retrying in {delay}s (attempt {job.attempts}/{job.max_attempts})")
        time.sleep(delay)
        job.status = JobStatus.PENDING
        save_job(conn, job)
    else:
        print(f"Job {job.id} exhausted retries, moving to dead-letter queue")
        move_to_dead_letter(conn, job)


def move_to_dead_letter(conn, job: Job) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO dead_letter (id, func_name, args, kwargs, attempts, failed_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))""",
        (job.id, job.func_name, json.dumps(job.args), json.dumps(job.kwargs), job.attempts),
    )
    conn.execute("DELETE FROM jobs WHERE id = ?", (job.id,))
    conn.commit()