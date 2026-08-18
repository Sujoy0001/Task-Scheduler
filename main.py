import json
import threading
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import tasks  # noqa: F401
from job import Job
from persistence import get_connection, save_job
from registry import get_task
from worker import worker_loop

BASE_DIR = Path(__file__).resolve().parent


class JobCreateRequest(BaseModel):
    task: str
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Task Scheduler", version="1.0.0")
_worker_thread: threading.Thread | None = None
_worker_running = False


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/jobs")
def list_jobs():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, func_name, args, kwargs, status, attempts, max_attempts, created_at
        FROM jobs
        ORDER BY created_at DESC
        """
    ).fetchall()

    jobs = []
    for row in rows:
        jobs.append(
            {
                "id": row[0],
                "task": row[1],
                "args": json.loads(row[2]),
                "kwargs": json.loads(row[3]),
                "status": row[4],
                "attempts": row[5],
                "max_attempts": row[6],
                "created_at": row[7],
            }
        )
    return jobs


@app.post("/api/jobs")
def create_job(payload: JobCreateRequest):
    try:
        get_task(payload.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    conn = get_connection()
    job = Job(func_name=payload.task, args=tuple(payload.args), kwargs=payload.kwargs)
    save_job(conn, job)

    return {
        "id": job.id,
        "task": job.func_name,
        "status": job.status.value,
        "args": list(job.args),
        "kwargs": job.kwargs,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
    }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id, func_name, args, kwargs, status, attempts, max_attempts, created_at
        FROM jobs WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": row[0],
        "task": row[1],
        "args": json.loads(row[2]),
        "kwargs": json.loads(row[3]),
        "status": row[4],
        "attempts": row[5],
        "max_attempts": row[6],
        "created_at": row[7],
    }


@app.post("/api/worker/start")
def start_worker():
    global _worker_thread, _worker_running

    if _worker_running and _worker_thread is not None and _worker_thread.is_alive():
        return {"status": "already_running"}

    def run_worker():
        global _worker_running
        _worker_running = True
        try:
            worker_loop()
        finally:
            _worker_running = False

    _worker_thread = threading.Thread(target=run_worker, daemon=True)
    _worker_thread.start()
    return {"status": "started"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
