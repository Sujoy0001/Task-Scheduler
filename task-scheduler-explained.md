# Task Scheduler — Step-by-Step Project Explanation

This document walks through **how the project actually works**, file by file,
in the order data flows through the system — from submitting a job to it
succeeding, failing, retrying, or landing in the dead-letter queue.

Use this to explain the project in interviews or to refresh your own memory
before a review.

---

## The Big Picture

```
   You (CLI)                Worker Process(es)              Storage
┌───────────────┐         ┌─────────────────────┐      ┌───────────────┐
│ submit a job  │───────▶ │  claim next PENDING  │◀────▶│  SQLite (WAL)  │
│ check status  │         │  job → RUNNING       │      │  jobs table    │
│ list DLQ      │         │  run the function    │      │  dead_letter   │
└───────────────┘         │  → SUCCESS or retry  │      └───────────────┘
                           └─────────────────────┘
```

One process submits jobs. One or more separate worker processes pull jobs
off the queue and execute them. Everything about a job's state lives in
SQLite, so if a worker crashes mid-job, nothing is lost — the next worker
that starts up can pick up where things left off.

---

## Step 1: Defining What a "Job" Is (`job.py`)

Every unit of work is represented by a `Job`:

```python
Job(
    id="auto-generated-uuid",
    func_name="send_email",
    args=(),
    kwargs={"to": "a@b.com", "subject": "Hi"},
    status=JobStatus.PENDING,
    attempts=0,
    max_retries=3,
)
```

- `func_name` — the name of the function to run (not the function itself —
  this is important, see Step 2)
- `status` — one of `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`
- `attempts` — how many times this job has been tried
- `max_retries` — after this many failures, the job is given up on

**Why store `func_name` as a string instead of the function itself?**
Because a `Job` needs to be saved to a database as plain data (text/JSON).
You can't store a live Python function inside SQLite — so instead, the job
just remembers the *name*, and something else is responsible for turning
that name back into a callable function. That's the registry's job.

---
//
## Step 2: The Task Registry (`registry.py` + `tasks.py`)

```python
@task
def send_email(to, subject):
    return f"Email sent to {to}"
```

The `@task` decorator does one simple thing: it adds the function to a
dictionary, `TASK_REGISTRY`, keyed by its name:

```python
TASK_REGISTRY = {
    "send_email": <function send_email>,
    "resize_image": <function resize_image>,
}
```

So later, when a worker has a `Job` with `func_name="send_email"`, it can do:

```python
func = TASK_REGISTRY["send_email"]
func(*job.args, **job.kwargs)
```

This is the exact pattern real tools like Celery use (`@app.task`). It's
what lets a job — just a string and some data — get turned back into
actual running code.

---

## Step 3: Submitting a Job (`cli.py` → `persistence.py`)

When you run:

```bash
uv run task-scheduler submit send_email --kwargs '{"to": "a@b.com"}'
```

Here's what happens:

1. `cli.py`'s `cmd_submit()` creates a `Job(func_name="send_email", kwargs={...})`
2. It calls `save_job()`, which `INSERT`s the job into the `jobs` table in
   SQLite with `status = PENDING`
3. The CLI prints the job's ID and exits — submission is fire-and-forget,
   a worker will pick it up whenever one is running

At this point the job just sits in the database, waiting.

---

## Step 4: A Worker Claims the Job (`worker.py` + `persistence.py`)

When you run:

```bash
uv run task-scheduler worker
```

`worker_loop()` starts an infinite loop:

```python
while True:
    job = fetch_next_pending(conn)
    if job is None:
        time.sleep(poll_interval)   # nothing to do, wait and check again
        continue
    run_job(conn, job)
```

The interesting part is `fetch_next_pending()` in `persistence.py`. This is
where **race conditions** are prevented. If you have 3 workers running at
once, you don't want two of them grabbing the same job. So this function:

1. Starts a `BEGIN IMMEDIATE` transaction (locks the database for writing)
2. Selects the oldest `PENDING` job
3. Immediately flips its status to `RUNNING` and commits

Because the lock is held for the entire select-then-update, no other worker
can sneak in and grab the same row in between. This is the same core idea
behind `SELECT ... FOR UPDATE` in Postgres — just SQLite's version of it.

---

## Step 5: Running the Job (`worker.py`)

```python
def run_job(conn, job):
    try:
        func = get_task(job.func_name)      # look up the real function
        result = func(*job.args, **job.kwargs)
        job.status = JobStatus.SUCCESS
        save_job(conn, job)                  # write SUCCESS back to SQLite
    except Exception as e:
        handle_failure(conn, job)            # go to Step 6
```

If the function runs without raising an exception, the job is marked
`SUCCESS` and saved. Done.

If it raises *any* exception, control passes to the retry logic.

---

## Step 6: Retry with Backoff, or Dead-Letter (`retry.py`)

```python
def handle_failure(conn, job):
    job.attempts += 1

    if job.attempts < job.max_retries:
        delay = 2 ** job.attempts        # 2s, 4s, 8s...
        time.sleep(delay)
        job.status = JobStatus.PENDING   # back in the queue
        save_job(conn, job)
    else:
        move_to_dead_letter(conn, job)   # give up, log it permanently
```

This is **exponential backoff** — each retry waits longer than the last.
The reasoning: if a task fails because some external service (like an email
provider) is temporarily down, retrying immediately just hammers a broken
service. Waiting longer each time gives it a chance to recover.

Once a job has failed `max_retries` times, it's moved out of the `jobs`
table entirely and into the `dead_letter` table — a permanent record of
"this job could not be completed," so it doesn't get retried forever and
doesn't silently vanish either.

---

## Step 7: Checking on Jobs (`cli.py`)

Two read-only commands let you inspect the system:

```bash
uv run task-scheduler status <job_id>   # current status + attempt count
uv run task-scheduler dlq-list          # everything that permanently failed
```

Both just query SQLite directly — no special logic, just `SELECT` statements
against the `jobs` and `dead_letter` tables.

---

## Step 8: Logging Everything (`logging_setup.py`)

Every meaningful event — job picked up, succeeded, failed, retried,
dead-lettered — gets logged through a `JobLoggerAdapter` that automatically
tags each line with the job's ID:

```
2026-08-18 10:02:11 | INFO | worker | job_id=abc-123 | Picked up job | func=send_email
2026-08-18 10:02:11 | WARNING | worker | job_id=abc-123 | Job failed | error=ConnectionError
2026-08-18 10:02:13 | INFO | retry | job_id=abc-123 | Retrying after backoff | delay=2s
2026-08-18 10:02:15 | INFO | worker | job_id=abc-123 | Job succeeded | result=Email sent
```

Logs go to the console *and* to `logs/scheduler.log` (rotating, so it
doesn't grow forever). Anything at `ERROR` level also gets written
separately to `logs/errors.log`, so dead-lettered jobs are easy to scan
without digging through normal activity.

Because every line has `job_id=...`, you can trace one job's entire life —
from submission to final success or failure — just by grepping the logs.

---

## Putting It All Together: One Job's Full Journey

1. **Submit** — `cli.py submit` creates a `Job`, saves it as `PENDING`
2. **Claim** — a worker's `fetch_next_pending()` locks and grabs it, sets `RUNNING`
3. **Execute** — `worker.py` looks up the function via the registry and calls it
4. **Outcome A: Success** — status becomes `SUCCESS`, saved, done
5. **Outcome B: Failure** — `retry.py` increments `attempts`
   - If under `max_retries` → back to `PENDING` after a backoff delay → loop back to step 2
   - If at `max_retries` → moved to `dead_letter`, removed from active jobs
6. **Throughout** — every step is logged with the job's ID, so the whole
   journey is traceable after the fact

---

## What to Say If Asked "Walk Me Through Your Project"

> "Jobs are stored as rows in SQLite rather than kept in memory, so nothing
> is lost if a worker crashes. Workers claim jobs using an immediate
> transaction so two workers can never grab the same job. Failed jobs retry
> with exponential backoff, and after enough failures they're moved to a
> dead-letter table instead of retrying forever. Every step is logged with
> the job's ID so I can trace one job's full history end to end."

That's the whole system in four sentences — and now you know exactly which
file backs up each part of that claim.
