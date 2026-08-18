"""Submits a batch of jobs so you can watch multiple workers race for them."""

from persistence import get_connection, save_job
from job import Job

conn = get_connection()

for i in range(20):
    job = Job(func_name="send_email", kwargs={"to": f"user{i}@example.com", "subject": "Hi"})
    save_job(conn, job)

print("Submitted 20 jobs.")