"""Worker loop — pulls jobs, executes them, updates status."""

import time
from job import JobStatus
from registry import get_task
from persistence import get_connection, fetch_next_pending, save_job
from retry import handle_failure
import tasks  # noqa: F401 — registers @task functions


def run_job(conn, job) -> None:
    print(f"[worker] picked up job {job.id} ({job.func_name})")
    try:
        func = get_task(job.func_name)
        result = func(*job.args, **job.kwargs)
        job.status = JobStatus.SUCCESS
        save_job(conn, job)
        print(f"[worker] job {job.id} succeeded -> {result}")
    except Exception as e:
        print(f"[worker] job {job.id} failed -> {type(e).__name__}: {e}")
        handle_failure(conn, job)


def worker_loop(poll_interval: float = 1.0) -> None:
    conn = get_connection()
    print("[worker] started, polling for jobs...")
    while True:
        job = fetch_next_pending(conn)
        if job is None:
            time.sleep(poll_interval)
            continue
        run_job(conn, job)


if __name__ == "__main__":
    worker_loop()