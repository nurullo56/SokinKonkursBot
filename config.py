from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    bot_token: str = ""
    admin_ids: List[int] = field(default_factory=list)
    db_path: str = "/app/data/contest.db"
