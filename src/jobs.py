"""Job tracking + (stub) pipeline runner for user-uploaded CSV → v3 report.

v0 design notes:
- In-process state. A single uvicorn worker holds all jobs in `_JOBS` dict.
  Survives only as long as the process — fine for v0 demo; swap for SQLite
  or Redis when we need persistence / multi-worker.
- Rate limiting is per-IP, in-memory, sliding 24h window. Same caveats.
- The "pipeline" is currently a stub that walks through fake stages on a
  timer and resolves to a hard-coded pre-generated report. Real
  run.py + generate_v3.py integration happens after EC2 deps are ready
  (tasks #8-10).
"""
from __future__ import annotations

import asyncio
import csv
import io
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel

# ── Public schema ───────────────────────────────────────────────────────────

JobStatus = Literal["queued", "running", "done", "failed"]
PipelineStage = Literal[
    "validating",
    "planning",
    "pathway_analysis",
    "ppi_enrichment",
    "writing",
    "rendering",
    "done",
]

REQUIRED_CSV_COLUMNS: tuple[str, ...] = (
    "Protein",
    "Protein_definition",
    "HR[95%CI]",
    "P_value",
    "NB_individual",
    "NB_case",
)

MAX_PROTEINS_PER_JOB = 50
RATE_LIMIT_PER_IP_PER_DAY = 3
RATE_LIMIT_WINDOW_SECONDS = 24 * 60 * 60


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobView(BaseModel):
    """Snapshot of a job returned by GET /api/jobs/{id}."""
    job_id: str
    status: JobStatus
    disease_name: str
    email: str
    created_at: float
    updated_at: float
    stage: Optional[PipelineStage] = None
    stage_index: int = 0
    stage_total: int = 6
    error: Optional[str] = None
    report_url: Optional[str] = None


class CSVValidationError(Exception):
    """Raised when an uploaded CSV doesn't match the required schema."""


class RateLimitError(Exception):
    """Raised when a client IP has hit the per-day cap."""


# ── Internal state ──────────────────────────────────────────────────────────

@dataclass
class _Job:
    job_id: str
    disease_name: str
    email: str
    client_ip: str
    created_at: float
    updated_at: float
    status: JobStatus = "queued"
    stage: Optional[PipelineStage] = None
    stage_index: int = 0
    error: Optional[str] = None
    report_url: Optional[str] = None
    proteins: list[dict] = field(default_factory=list)

    def to_view(self) -> JobView:
        return JobView(
            job_id=self.job_id,
            status=self.status,
            disease_name=self.disease_name,
            email=self.email,
            created_at=self.created_at,
            updated_at=self.updated_at,
            stage=self.stage,
            stage_index=self.stage_index,
            stage_total=len(_STUB_STAGES),
            error=self.error,
            report_url=self.report_url,
        )


_JOBS: dict[str, _Job] = {}
_IP_LOG: dict[str, deque[float]] = {}


def _now() -> float:
    return time.time()


# ── CSV validation ──────────────────────────────────────────────────────────

def parse_and_validate_csv(raw_bytes: bytes) -> list[dict]:
    """Read CSV bytes, enforce schema and row cap, return list of row dicts."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise CSVValidationError(f"CSV must be UTF-8 encoded ({e})") from e

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise CSVValidationError("CSV is empty or has no header row")

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise CSVValidationError(
            "CSV is missing required columns: " + ", ".join(missing)
            + f". Required columns: {', '.join(REQUIRED_CSV_COLUMNS)}"
        )

    rows: list[dict] = []
    for i, row in enumerate(reader, start=2):  # row 1 = header
        if not (row.get("Protein") or "").strip():
            raise CSVValidationError(f"Row {i}: 'Protein' is empty")
        rows.append(row)
        if len(rows) > MAX_PROTEINS_PER_JOB:
            raise CSVValidationError(
                f"CSV has more than {MAX_PROTEINS_PER_JOB} rows (demo cap)"
            )

    if not rows:
        raise CSVValidationError("CSV has a header but no data rows")
    return rows


# ── Rate limiting ───────────────────────────────────────────────────────────

def check_rate_limit(client_ip: str) -> None:
    cutoff = _now() - RATE_LIMIT_WINDOW_SECONDS
    log = _IP_LOG.setdefault(client_ip, deque())
    while log and log[0] < cutoff:
        log.popleft()
    if len(log) >= RATE_LIMIT_PER_IP_PER_DAY:
        wait_seconds = int(RATE_LIMIT_WINDOW_SECONDS - (_now() - log[0]))
        raise RateLimitError(
            f"Rate limit: max {RATE_LIMIT_PER_IP_PER_DAY} jobs per IP per day. "
            f"Try again in ~{wait_seconds // 3600}h."
        )


def _record_rate_limit_hit(client_ip: str) -> None:
    _IP_LOG.setdefault(client_ip, deque()).append(_now())


# ── Job lifecycle ───────────────────────────────────────────────────────────

def create_job(
    *,
    disease_name: str,
    email: str,
    client_ip: str,
    proteins: list[dict],
) -> _Job:
    check_rate_limit(client_ip)
    _record_rate_limit_hit(client_ip)
    now = _now()
    job = _Job(
        job_id=uuid.uuid4().hex[:12],
        disease_name=disease_name,
        email=email,
        client_ip=client_ip,
        created_at=now,
        updated_at=now,
        proteins=proteins,
    )
    _JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> Optional[_Job]:
    return _JOBS.get(job_id)


# ── Stub pipeline (replace with real run.py + generate_v3.py later) ────────

# Each stage simulates work for a short interval. Total ~8s end-to-end.
_STUB_STAGES: list[tuple[PipelineStage, float]] = [
    ("planning", 1.5),
    ("pathway_analysis", 2.0),
    ("ppi_enrichment", 1.5),
    ("writing", 1.5),
    ("rendering", 1.0),
    ("done", 0.0),
]


async def run_pipeline_stub(job_id: str) -> None:
    """Background task: simulate the real pipeline for the upload-flow demo.

    Behavior:
      - Walks through stub stages with fake delays.
      - On success, points result_url at a hard-coded pre-generated report
        (Parkinson's). This lets the upload-flow UI be exercised end-to-end
        without spending real OpenAI tokens.
    """
    job = _JOBS.get(job_id)
    if job is None:
        return
    job.status = "running"
    job.stage = "validating"
    job.updated_at = _now()
    try:
        for idx, (stage, delay) in enumerate(_STUB_STAGES, start=1):
            await asyncio.sleep(delay)
            job.stage = stage
            job.stage_index = idx
            job.updated_at = _now()
        job.status = "done"
        # Until real pipeline lands: redirect everyone to the Parkinson's report
        # as a placeholder so the UI flow is testable.
        job.report_url = (
            "/raw?file=parkinsons/Parkinson%27s_disease_v3_auto.html"
        )
    except Exception as e:  # pragma: no cover — defensive
        job.status = "failed"
        job.error = f"Pipeline error: {e}"
        job.updated_at = _now()
