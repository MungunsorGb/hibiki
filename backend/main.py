"""
main.py - HIBIKI-AI backend

Serves:
  - JSON API for triggering ESP32 taps and classifying them with fixed,
    uncalibrated thresholds (see backend/features.py).
  - The frontend (static files in ../frontend) at "/".

No trained ML model and no baseline calibration exist yet. Each tap is
classified independently using fixed placeholder thresholds. Points are
appended in the order they're taken, along a straight line, matching the
robot's straight-line movement.

/esp32/tap-sim generates synthetic data for UI/demo testing when real
ESP32 hardware is unavailable. Simulated results are always labeled
[SIMULATED] and must never be presented as real inspection data.
"""
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from backend.report import generate_pdf

from backend.esp32_bridge import fetch_and_parse, ESP32Error
from backend.features import summarize, classify_by_magnitude

app = FastAPI(title="HIBIKI-AI Backend")

STATE = {
    "esp32_ip": None,
    "points": [],
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


def _fake_reading():
    n = 200
    xs = [5.6 + random.uniform(-0.3, 0.3) for _ in range(n)]
    ys = [8.0 + random.uniform(-0.3, 0.3) for _ in range(n)]
    zs = [3.4 + random.uniform(-0.5, 1.5) for _ in range(n)]
    return xs, ys, zs


@app.post("/esp32/tap")
def tap(req: TapRequest):
    ip = _resolve_ip(req.esp32_ip)
    try:
        xs, ys, zs = fetch_and_parse(ip, trigger=True)
    except ESP32Error as e:
        raise HTTPException(status_code=502, detail=str(e))

    summary = summarize(xs, ys, zs)
    result = classify_by_magnitude(summary)

    point = {
        "label": req.label,
        "order": len(STATE["points"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "classification": result["classification"],
        "method": result["method"],
        "raw": {"x": xs, "y": ys, "z": zs},
    }
    STATE["points"].append(point)
    return point


@app.post("/esp32/tap-sim")
def tap_simulated(req: TapRequest):
    xs, ys, zs = _fake_reading()
    summary = summarize(xs, ys, zs)
    result = classify_by_magnitude(summary)

    point = {
        "label": req.label + " [SIMULATED]",
        "order": len(STATE["points"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "classification": result["classification"],
        "method": result["method"] + " [SIMULATED DATA]",
        "raw": {"x": xs, "y": ys, "z": zs},
    }
    STATE["points"].append(point)
    return point

@app.get("/report/pdf")
def report_pdf():
    if not STATE["points"]:
        raise HTTPException(status_code=400, detail="No inspection points to report yet.")
    pdf_bytes = generate_pdf(STATE["points"])
    filename = f"hibiki_ai_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/points")
def get_points():
    return {"points": STATE["points"]}


@app.delete("/points")
def clear_points():
    STATE["points"] = []
    return {"status": "cleared"}


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
