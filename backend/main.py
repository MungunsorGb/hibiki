"""
main.py - HIBIKI-AI backend

Serves:
  - JSON API for triggering ESP32 taps, setting a baseline, classifying
    taps by deviation from that baseline, and storing inspection points.
  - The frontend (static files in ../frontend) at "/".

No trained ML model exists yet. Classification is rule-based threshold
comparison against a baseline you set. See backend/features.py.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.esp32_bridge import fetch_and_parse, ESP32Error
from backend.features import summarize, classify_against_baseline

app = FastAPI(title="HIBIKI-AI Backend")

# --- in-memory state (resets when server restarts; fine for today's demo) ---
STATE = {
    "esp32_ip": None,
    "baseline": None,      # feature summary dict, or None
    "baseline_raw": None,  # raw x,y,z of baseline, for reference
    "points": [],          # list of inspection point results
}


class VibrationSample(BaseModel):
    x: List[float]
    y: List[float]
    z: List[float]
    sample_rate_hz: Optional[float] = None


class InspectionResult(BaseModel):
    status: str
    model_status: str
    damage_class: Optional[str]
    confidence: Optional[float]
    n_samples_received: int
    timestamp_utc: str
    note: str


class ESP32Config(BaseModel):
    esp32_ip: str


class TapRequest(BaseModel):
    label: str = "Unlabeled point"
    esp32_ip: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "HIBIKI-AI backend"}


@app.post("/inspect", response_model=InspectionResult)
def inspect(data: VibrationSample):
    """Kept from earlier testing: accepts raw data directly, no ESP32 call."""
    n = len(data.x)
    if not (len(data.x) == len(data.y) == len(data.z)):
        raise HTTPException(status_code=400, detail="x, y, z must be the same length.")
    if n == 0:
        raise HTTPException(status_code=400, detail="No data received.")
    return InspectionResult(
        status="received",
        model_status="PLACEHOLDER - no trained model loaded yet",
        damage_class=None,
        confidence=None,
        n_samples_received=n,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        note="Raw ingestion test only.",
    )


@app.post("/esp32/config")
def set_esp32_config(cfg: ESP32Config):
    STATE["esp32_ip"] = cfg.esp32_ip
    return {"esp32_ip": STATE["esp32_ip"]}


@app.get("/esp32/config")
def get_esp32_config():
    return {"esp32_ip": STATE["esp32_ip"]}


def _resolve_ip(esp32_ip: Optional[str]) -> str:
    ip = esp32_ip or STATE["esp32_ip"]
    if not ip:
        raise HTTPException(status_code=400, detail="No ESP32 IP set. Call /esp32/config first.")
    return ip


@app.post("/esp32/baseline")
def set_baseline(req: TapRequest):
    ip = _resolve_ip(req.esp32_ip)
    try:
        xs, ys, zs = fetch_and_parse(ip, trigger=True)
    except ESP32Error as e:
        raise HTTPException(status_code=502, detail=str(e))

    summary = summarize(xs, ys, zs)
    STATE["baseline"] = summary
    STATE["baseline_raw"] = {"x": xs, "y": ys, "z": zs}
    return {
        "status": "baseline_set",
        "summary": summary,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/esp32/tap")
def tap(req: TapRequest):
    ip = _resolve_ip(req.esp32_ip)
    if STATE["baseline"] is None:
        raise HTTPException(status_code=400, detail="No baseline set yet. Call /esp32/baseline first.")

    try:
        xs, ys, zs = fetch_and_parse(ip, trigger=True)
    except ESP32Error as e:
        raise HTTPException(status_code=502, detail=str(e))

    summary = summarize(xs, ys, zs)
    result = classify_against_baseline(summary, STATE["baseline"])

    point = {
        "label": req.label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "classification": result["classification"],
        "deviation_pct": result["deviation_pct"],
        "method": result["method"],
        "raw": {"x": xs, "y": ys, "z": zs},
    }
    STATE["points"].append(point)
    return point


@app.get("/points")
def get_points():
    return {"points": STATE["points"], "baseline_set": STATE["baseline"] is not None}


@app.delete("/points")
def clear_points():
    STATE["points"] = []
    STATE["baseline"] = None
    STATE["baseline_raw"] = None
    return {"status": "cleared"}


# --- serve the frontend (must be registered AFTER the API routes above) ---
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")