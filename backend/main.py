"""
main.py - HIBIKI-AI backend skeleton (Step 1 of system integration)

This server does ONE thing right now: accepts vibration data and returns
a PLACEHOLDER classification. It is NOT a trained model. Every response
says so explicitly, so nobody mistakes this for a real result.

Run with:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

Then ESP32 or Flutter can POST to:  http://<your-computer-ip>:8000/inspect
"""

from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="HIBIKI-AI Backend", version="0.1.0-skeleton")


class VibrationSample(BaseModel):
    x: List[float] = Field(..., description="X-axis readings")
    y: List[float] = Field(..., description="Y-axis readings")
    z: List[float] = Field(..., description="Z-axis readings")
    sample_rate_hz: float | None = Field(
        default=None,
        description="Sampling rate in Hz, if known. Leave null if unknown."
    )


class InspectionResult(BaseModel):
    status: str
    model_status: str
    damage_class: str | None
    confidence: float | None
    n_samples_received: int
    timestamp_utc: str
    note: str


@app.get("/health")
def health():
    """Quick check that the server is running. Flutter can ping this first."""
    return {"status": "ok", "service": "HIBIKI-AI backend"}


@app.post("/inspect", response_model=InspectionResult)
def inspect(data: VibrationSample):
    """
    Receives raw X,Y,Z vibration data (from ESP32, or from Flutter relaying it)
    and returns a result.

    RIGHT NOW this returns a PLACEHOLDER result — no model has been trained yet.
    Tomorrow, once real data + a trained model exist, only the inside of this
    function changes (features get extracted, real model runs). The request
    and response shape will stay the same, so Flutter does not need to change.
    """
    n = len(data.x)
    if not (len(data.x) == len(data.y) == len(data.z)):
        raise HTTPException(status_code=400, detail="x, y, z must be the same length.")
    if n == 0:
        raise HTTPException(status_code=400, detail="No data received.")

    # --- PLACEHOLDER PREDICTION ---
    # No real model exists yet. We deliberately do NOT fabricate a damage
    # class or a confidence score. We only confirm the data was received.
    return InspectionResult(
        status="received",
        model_status="PLACEHOLDER - no trained model loaded yet",
        damage_class=None,
        confidence=None,
        n_samples_received=n,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        note=(
            "This is a wiring test only. Real classification will be added "
            "once real vibration data is collected and a model is trained."
        ),
    )