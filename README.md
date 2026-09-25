# HIBIKI

HIBIKI is a small bridge inspection robot project developed for NAPROCK / PROCON 2026.

The main idea of the project is to make steel bridge inspection safer and easier.
Instead of checking every point manually, the robot can move along a steel surface,
create a small impact using a solenoid, record the vibration response, and classify
the condition of the steel.

The system currently focuses on three conditions:

- Healthy / Normal Steel
- Corrosion
- Loose Bolt

## How HIBIKI Works

The basic inspection process is:

1. The robot is placed on the steel surface.
2. Magnetic wheels help the robot stay attached to the steel.
3. The robot stops at an inspection point.
4. A solenoid creates an impact on the steel.
5. The vibration sensor records the response in three axes: `X`, `Y`, and `Z`.
6. The ESP32 sends the measurement to the web application.
7. The backend processes the vibration data.
8. The AI model classifies the result as:
   - Healthy
   - Corrosion
   - Loose Bolt
9. The result is shown on the web application.
10. The user can press the **Move Forward** button to move the robot to the next inspection point.

## System Overview

The HIBIKI system is made of three main parts:

### Robot

The robot contains:

- ESP32
- DC motors
- Magnetic wheels
- Motor driver
- Solenoid
- Vibration sensor
- Steel inspection mechanism

### Web Application

The web application is used to:

- Check the robot connection
- Start a measurement
- View vibration data
- View classification results
- Move the robot forward
- Check the current robot status

### AI / Data Processing

The backend receives three-axis vibration data (`X`, `Y`, `Z`) from each impact,
extracts a fixed set of time-domain features from it, and classifies the result.

## Repository layout

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
data/sample/             Labeled training data goes here .
```

## Running it

```
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000`, enter the ESP32's IP address (shown on
its Serial Monitor at boot — see `firmware/esp32_sensor/README.md`), and
start inspecting.
