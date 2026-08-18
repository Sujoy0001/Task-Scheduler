"""CLI entrypoint: submit jobs, check status, start workers, inspect the DLQ."""

import argparse
import json
from job import Job
from persistence import get_connection, save_job
from worker import worker_loop


def cmd_submit(args):
    conn = get_connection()
    job = Job(func_name=args.task, kwargs=json.loads(args.kwargs or "{}"))
    save_job(conn, job)
    print(f"Submitted job {job.id} ({job.func_name})")


def cmd_status(args):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, status, attempts FROM jobs WHERE id = ?", (args.job_id,)
    ).fetchone()
    if row is None:
        print("Job not found (it may have completed or been dead-lettered)")
    else:
        print(f"id={row[0]} status={row[1]} attempts={row[2]}")


def cmd_worker(args):
    conn = get_connection()
    worker_loop(conn, poll_interval=1.0)


def cmd_dlq_list(args):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, func_name, attempts, failed_at FROM dead_letter"
    ).fetchall()
    if not rows:
        print("Dead-letter queue is empty")
    for row in rows:
        print(f"id={row[0]} func={row[1]} attempts={row[2]} failed_at={row[3]}")


def main():
    parser = argparse.ArgumentParser(prog="scheduler")
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="Submit a new job")
    p_submit.add_argument("task", help="Registered task name, e.g. send_email")
    p_submit.add_argument("--kwargs", help='JSON string of kwargs, e.g. \'{"to": "a@b.com"}\'')
    p_submit.set_defaults(func=cmd_submit)

    p_status = sub.add_parser("status", help="Check a job's status")
    p_status.add_argument("job_id")
    p_status.set_defaults(func=cmd_status)

    p_worker = sub.add_parser("worker", help="Start a worker process")
    p_worker.set_defaults(func=cmd_worker)

    p_dlq = sub.add_parser("dlq-list", help="List dead-lettered jobs")
    p_dlq.set_defaults(func=cmd_dlq_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()