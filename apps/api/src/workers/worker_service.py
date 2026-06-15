"""Pipeline Worker — Cloud Run Service with per-stage Cloud Tasks endpoints."""
import logging

import google.auth.transport.requests
import google.oauth2.id_token
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from src.workers.pipeline import run_stage
from src.workers.pipeline_control import PipelineHalted

logger = logging.getLogger(__name__)

worker_app = FastAPI(title="SAMAA Pipeline Worker")

# Audience must match the Cloud Run service URL configured in Cloud Tasks
CLOUD_TASKS_AUDIENCE = "https://your-worker-service-url.run.app"

# Map URL paths to stage indices for cross-validation
STAGE_PATH_TO_INDEX: dict[str, int] = {
    "/stage/preprocess":   0,
    "/stage/stt":          1,
    "/stage/diarization":  2,
    "/stage/turns":        3,
    "/stage/roles":        4,
    "/stage/segmentation": 5,
    "/stage/stitch":       6,
    "/stage/analyze":      7,
    "/stage/scoring":      8,
}


class PipelineTask(BaseModel):
    recording_id: str
    pipeline_version: str = "v1"
    stage_index: int = 0


def _verify_cloud_tasks_oidc(request: Request) -> None:
    """Verify the OIDC token attached by Cloud Tasks.

    Cloud Tasks signs requests with a service account OIDC token.
    Raises HTTPException 401 if the token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header.removeprefix("Bearer ")
    try:
        google.oauth2.id_token.verify_firebase_token(
            token,
            google.auth.transport.requests.Request(),
            audience=CLOUD_TASKS_AUDIENCE,
        )
    except Exception as e:
        logger.warning("OIDC token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid OIDC token") from e


@worker_app.get("/health")
def health():
    """Required for Cloud Run startup probes."""
    return {"status": "ok"}


@worker_app.post("/stage/preprocess")
@worker_app.post("/stage/stt")
@worker_app.post("/stage/diarization")
@worker_app.post("/stage/turns")
@worker_app.post("/stage/roles")
@worker_app.post("/stage/segmentation")
@worker_app.post("/stage/stitch")
@worker_app.post("/stage/analyze")
@worker_app.post("/stage/scoring")
def process_stage(task: PipelineTask, request: Request):
    """Execute a single pipeline stage dispatched by Cloud Tasks.

    Returns 200 on success, halt, or idempotency skip — all cases where
    Cloud Tasks must NOT retry. Raises 500 only for transient failures
    where a retry is appropriate.
    """
    _verify_cloud_tasks_oidc(request)

    # Cross-validate URL path vs stage_index to catch misconfigured tasks
    actual_path = request.url.path
    expected_index = STAGE_PATH_TO_INDEX.get(actual_path)
    if expected_index is None:
        raise HTTPException(status_code=404, detail=f"Unknown stage path: {actual_path}")
    if task.stage_index != expected_index:
        logger.error(
            "Stage index mismatch: URL=%s expects index=%d, body has index=%d",
            actual_path, expected_index, task.stage_index,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"stage_index mismatch: '{actual_path}' expects {expected_index}, "
                f"got {task.stage_index}"
            ),
        )

    logger.info(
        "[%s] Processing stage %s (index %d, pipeline %s)",
        task.recording_id, actual_path, task.stage_index, task.pipeline_version,
    )

    try:
        run_stage(task.recording_id, task.pipeline_version, task.stage_index)
    except PipelineHalted as e:
        # Halt = validation failure, do not retry. Return 200 so Cloud Tasks
        # drops this task. The recording is already marked FAILED by fail_and_halt().
        logger.warning(
            "[%s] Pipeline halted at %s: %s — returning 200 to suppress retry",
            task.recording_id, actual_path, e,
        )
        return {
            "status": "halted",
            "recording_id": task.recording_id,
            "stage": actual_path,
            "reason": str(e),
        }
    except Exception as e:
        # Transient failure — log with full context and let Cloud Tasks retry (500)
        logger.error(
            "[%s] Stage %s failed unexpectedly: %s",
            task.recording_id, actual_path, e, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Stage '{actual_path}' failed: {e}",
        ) from e

    return {
        "status": "completed",
        "recording_id": task.recording_id,
        "stage": actual_path,
    }