import time

from job import Job, JobStatus
from registry import get_task
from persistence import get_connection, fetch_next_pending, save_job
from retry import handle_failure
import tasks  # noqa: F401 — registers @task functions


def submit_job(conn, job: Job) -> None:
    """
    Submits a job by saving it to the database as PENDING.
    """
    save_job(conn, job)
    print(f"Job {job.id} submitted: {job.func_name}")


def run_job(conn, job: Job) -> None:
    try:
        func = get_task(job.func_name)
        result = func(*job.args, **job.kwargs)
        job.status = JobStatus.SUCCESS
        save_job(conn, job)
        print(f"Job {job.id} succeeded -> {result}")
    except Exception as e:
        print(f"Job {job.id} failed -> {type(e).__name__}: {e}")
        handle_failure(conn, job)


def worker_loop(conn, poll_interval: float = 1.0) -> None:
    """
    Worker loop that pulls PENDING jobs from the database and processes them.
    """
    print("Worker started. Waiting for jobs...")
    while True:
        job = fetch_next_pending(conn)
        if job is None:
            time.sleep(poll_interval)
            continue
        run_job(conn, job)


if __name__ == "__main__":
    conn = get_connection()

    # Submit a couple of jobs
    submit_job(conn, Job(func_name="send_email", kwargs={"to": "a@b.com", "subject": "Hi"}))
    submit_job(conn, Job(func_name="resize_image", kwargs={"path": "photo.jpg", "width": 100, "height": 100}))

    # Process everything currently pending, once, then exit
    while True:
        job = fetch_next_pending(conn)
        if job is None:
            break
        run_job(conn, job)