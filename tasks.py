from registry import task
import random

@task
def flaky_task():
    if random.random() < 0.7:
        raise ConnectionError("Simulated failure")
    return "Finally succeeded!"


@task
def send_email(to: str, subject: str) -> str:
    """
    Simulates sending an email.
    """
    return f"Email sent to {to} with subject '{subject}'"

@task
def resize_image(path: str, width: int, height: int) -> str:
    """
    Simulates resizing an image.
    """
    return f"Image at {path} resized to {width}x{height}"