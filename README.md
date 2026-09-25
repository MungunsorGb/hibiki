# HIBIKI-AI

A tap-based structural inspection robot: an ESP32-mounted accelerometer
taps a surface, the robot moves along it in a straight line, and each tap
is classified into a damage category and shown live in a web dashboard
with a downloadable PDF report at the end.

## Architecture

```
firmware/esp32_sensor/   Arduino sketch: captures tap accelerometer data,
                          serves it over HTTP, drives the motors.
backend/                 FastAPI server: talks to the ESP32, extracts
                          features, classifies each tap, serves the
                          frontend, generates the PDF report.
ai/src/                  Offline tooling: dataset inspection and
                          classifier training (produces
                          ai/models/classifier.joblib).
frontend/                Static web dashboard (vanilla HTML/CSS/JS).
data/sample/              Labeled training data goes here (not committed
                          by default — see data/sample/README.md).
```

## Running it

```
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000`, enter the ESP32's IP address (shown on
its Serial Monitor at boot — see `firmware/esp32_sensor/README.md`), and
start inspecting.

## Classification: how it actually works today

`backend/main.py` picks one of two paths, and every result is labeled
with which one produced it:

- **Trained model** (`ai/models/classifier.joblib`), if present — a real
  scikit-learn classifier trained on your own labeled Healthy / Corrosion
  / Loose Bolt tap recordings. Train it with:
  ```
  python ai/src/train_classifier.py
  ```
  after adding labeled CSVs under `data/sample/<ClassName>/` (see
  `data/sample/README.md` for the exact format).
- **Fixed-threshold fallback**, used automatically whenever no trained
  model file exists. This is a simple, uncalibrated rule on peak-to-peak
  vibration magnitude — not a trained model, and never presented as one.
  It exists so the pipeline is runnable end-to-end even before a real
  dataset is collected.

There is no simulated/demo data path in this backend. Every point shown
in the app or included in a PDF report is a real ESP32 sensor reading, or
the request fails with an explicit error.

## Movement

No wheel encoders exist on this robot, so "Move Forward" is a
**duration-based** move (`/go`, wait, `/stop`), not a calibrated
**distance**-based one — see `firmware/esp32_sensor/README.md` for how to
calibrate `MOVE_DURATION_MS` in `backend/main.py` against a real measured
distance.

## Known limitations, stated plainly

- The fixed-threshold classifier fallback has not been validated against
  real damaged specimens; it's a placeholder until a trained model exists.
- `firmware/esp32_sensor/esp32_sensor.ino` is a reference implementation
  (assumes an MPU6050 on default I2C pins) and has not been verified
  against this robot's exact wiring.
- Move duration is not yet calibrated to a real distance.
- `data/sample/` ships empty; a trained model requires adding real labeled
  data first.
