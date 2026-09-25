# ESP32 firmware

## Setup

1. Install the Arduino libraries: `WiFi`, `WebServer` (bundled with the
   ESP32 board package), `Adafruit_MPU6050`, `Adafruit_Sensor`,
   `Adafruit_BusIO`.
2. Copy the credentials template and fill in your real network:
   ```
   cp secrets.h.example secrets.h
   ```
   `secrets.h` is gitignored — it is never committed, and no real Wi-Fi
   credentials exist anywhere in this repo or its history.
3. Open `esp32_sensor.ino` in the Arduino IDE, check `PIN_MOTOR_A` /
   `PIN_MOTOR_B` match your actual motor driver wiring, and flash.
4. Open the Serial Monitor at 115200 baud to read the ESP32's IP address
   once it connects, and enter that IP in the HIBIKI-AI dashboard.

`esp32_sensor.ino` is a **reference implementation**: it assumes an
MPU6050 on the ESP32's default I2C pins. It has not been run against this
specific robot's wiring — verify pins/sensor model before trusting it on
real hardware, and update the `PIN_*` / sensor setup if yours differs.

## HTTP contract the backend expects

The backend (`backend/esp32_bridge.py`) talks to three endpoints:

| Endpoint | Method | Behavior |
|---|---|---|
| `/tap`  | GET | Captures one tap's worth of accelerometer samples and returns an HTML page containing `<textarea>X,Y,Z` / `X,Y,Z` / ... `</textarea>`. Backend regex-scrapes the `<textarea>` and parses CSV rows. |
| `/go`   | GET | Starts driving forward. Runs until `/stop` is called — the ESP32 does not decide duration itself. |
| `/stop` | GET | Stops driving. |

Movement duration is controlled entirely from the backend
(`backend/esp32_bridge.py: trigger_move()`), which calls `/go`, sleeps for
a configured number of milliseconds, then calls `/stop`. This keeps all
timing logic in one place instead of split across firmware and backend.

## Sampling rate

The firmware measures its own real sampling rate with `micros()` during
each tap capture and reports it in the response (`# SAMPLE_RATE_HZ=...`
comment line), instead of requiring a guessed value to be typed into the
dashboard anywhere.

## Movement calibration — not yet done

There are no wheel encoders on this robot (confirmed), so `/go` + `/stop`
timed by the backend is a **duration-based** move, not a **distance**-based
one. `MOVE_DURATION_MS` in `backend/main.py` is a placeholder run time —
it has not been calibrated against real measured distance.

To calibrate it for real:
1. Mark a known distance (e.g. 500 mm) on the floor.
2. Drive the robot forward at the normal command from a stop, and time it
   with a stopwatch.
3. Compute mm/ms and update `MOVE_DURATION_MS` (or extend
   `backend/main.py` to accept a target distance and convert).

Until that measurement exists, the app only ever reports how long a move
ran for, not how far the robot travelled.
