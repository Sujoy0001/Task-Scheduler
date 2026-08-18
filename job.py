from dataclasses import dataclass, field
from datetime import datetime, timezone

from enum import Enum
import uuid


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    
@dataclass
class Job:
    func_name : str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    id : str = field(default_factory=lambda: str(uuid.uuid4()))
    status : JobStatus = JobStatus.PENDING
    attempts : int = 0
    max_attempts : int = 3
    created_at : datetime = field(default_factory=lambda: datetime.now(timezone.utc))