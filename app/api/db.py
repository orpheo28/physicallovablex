"""SQLite persistence (SQLModel). Owner: W0.

Artifacts are stored as validated JSON documents (one row per project × stage), which keeps the contract in
`contracts/artifacts.py` as the single schema. PRD §13 entities (BOMItem, DFMIssue, Quote, ...) live inside
those documents; the simulated network (factories, RFQs, quotes) is owned by W5 (mcp/).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Field, Session, SQLModel, create_engine, select

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent / "data" / "app.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
# timeout = busy wait of the driver; WAL lets readers (GET /projects/{id} polls) run while a background autorun writes.
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False, "timeout": 5},
                       pool_size=20, max_overflow=20, pool_timeout=10)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectRow(SQLModel, table=True):
    __tablename__ = "project"
    id: str = Field(primary_key=True)
    data: str  # contracts.Project JSON
    created_at: datetime = Field(default_factory=_now)


class ArtifactRow(SQLModel, table=True):
    __tablename__ = "artifact"
    project_id: str = Field(primary_key=True)
    stage: int = Field(primary_key=True)  # 1-13; 0 = Factory Pack
    data: str  # contracts stage artifact JSON
    status: str = "draft"
    fallback: bool = False
    updated_at: datetime = Field(default_factory=_now)


class AutorunRow(SQLModel, table=True):
    __tablename__ = "autorun"
    project_id: str = Field(primary_key=True)
    data: str  # contracts.AutorunStatus JSON


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def session() -> Session:
    return Session(engine)


__all__ = ["ArtifactRow", "AutorunRow", "ProjectRow", "engine", "init_db", "reset_db", "select", "session"]
