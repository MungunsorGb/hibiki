"""
main.py - HIBIKI-AI backend

Serves:
  - JSON API for triggering ESP32 taps and classifying them.
  - JSON API for triggering a fixed-duration forward move.
  - The frontend (static files in ../frontend) at "/".

Classification: if ai/models/classifier.joblib exists, it is a real
scikit-learn model trained by ai/src/train_classifier.py on labeled
Healthy / Corrosion / LooseBolt taps, and is used for every /esp32/tap
request. If that file does not exist, every response instead uses
classify_by_magnitude(), a fixed uncalibrated threshold rule, and is
labeled as such in its "method" field so the two can never be confused
in the UI or the PDF report. There is no simulated/fake data path in
this backend -- every point is either a real ESP32 reading or the
request fails with an error.

Movement: MOVE_DURATION_MS below is a placeholder run time for
"Move Forward", NOT a calibrated distance. No wheel encoders exist on
this robot, so there is no way to close the loop on real distance
travelled without a real calibration measurement (drive at the normal
command, time a known distance with a stopwatch, compute mm/ms). Until
that measurement is supplied, this endpoint honestly reports the
duration it ran for and does not claim a distance value.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel

from backend.report import generate_pdf
from backend.esp32_bridge import fetch_and_parse, trigger_move, ESP32Error
from backend.features import summarize, extract_feature_vector, classify_by_magnitude

app = FastAPI(title="HIBIKI-AI Backend")

STATE = {
    "esp32_ip": None,
    "points": [],
}

MODEL_PATH = Path(__file__).resolve().parent.parent / "ai" / "models" / "classifier.joblib"

# Placeholder run time for a forward move. NOT a calibrated distance --
# see module docstring. Replace once a real mm/ms measurement exists,
# and turn this into an actual distance-based calculation at that point.
MOVE_DURATION_MS = 1000


def _load_model():
    if not MODEL_PATH.exists():
        return None
    import joblib
    try:
        bundle = joblib.load(MODEL_PATH)
        return bundle
    except Exception:
        return None


def classify(xs: List[float], ys: List[float], zs: List[float], summary: dict) -> dict:
    """Single source of truth for turning a tap into a classification.
    Picks the trained model if one exists, otherwise the honest fallback."""
    bundle = _load_model()
    if bundle is not None:
        model = bundle["model"]
        feats = [extract_feature_vector(xs, ys, zs)]
        pred = model.predict(feats)[0]
        proba = None
        if hasattr(model, "predict_proba"):
            classes = list(model.classes_)
            probs = model.predict_proba(feats)[0]
            proba = round(float(probs[classes.index(pred)]), 4)
        return {
            "classification": pred,
            "confidence": proba,
            "method": "trained-classifier (RandomForest, ai/models/classifier.joblib)",
        }
    fallback = classify_by_magnitude(summary)
    return {
        "classification": fallback["classification"],
        "confidence": fallback["confidence"],
        "method": fallback["method"],
    }


class ESP32Config(BaseModel):
    esp32_ip: str


class TapRequest(BaseModel):
    label: str = "Unlabeled point"
    esp32_ip: Optional[str] = None


class MoveRequest(BaseModel):
    esp32_ip: Optional[str] = None
    duration_ms: Optional[int] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "HIBIKI-AI backend", "model_loaded": MODEL_PATH.exists()}


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


@app.post("/esp32/tap")
def tap(req: TapRequest):
    ip = _resolve_ip(req.esp32_ip)
    try:
        xs, ys, zs = fetch_and_parse(ip, trigger=True)
    except ESP32Error as e:
        raise HTTPException(status_code=502, detail=str(e))

    summary = summarize(xs, ys, zs)
    result = classify(xs, ys, zs, summary)

    point = {
        "label": req.label,
        "order": len(STATE["points"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "classification": result["classification"],
        "confidence": result["confidence"],
        "method": result["method"],
        "raw": {"x": xs, "y": ys, "z": zs},
    }
    STATE["points"].append(point)
    return point


@app.post("/esp32/move")
def move(req: MoveRequest):
    ip = _resolve_ip(req.esp32_ip)
    duration_ms = req.duration_ms or MOVE_DURATION_MS
    try:
        trigger_move(ip, duration_ms)
    except ESP32Error as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "status": "moved",
        "duration_ms": duration_ms,
        "note": "Duration-based move, NOT a calibrated distance (no wheel encoders). "
                "See MOVE_DURATION_MS in backend/main.py.",
    }


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
