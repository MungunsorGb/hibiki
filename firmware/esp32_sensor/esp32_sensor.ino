/*
  esp32_sensor.ino - HIBIKI-AI reference ESP32 firmware

  ============================== IMPORTANT ==============================
  This is a REFERENCE / STARTER implementation, not verified against your
  specific wiring. It assumes an MPU6050 accelerometer on the ESP32's
  DEFAULT I2C pins (SDA = GPIO 21, SCL = GPIO 22) and a two-pin H-bridge
  style drive output on GPIO 25/26. If your actual robot wires the sensor
  or motors differently, update PIN_* below before flashing -- do not
  assume this matches your hardware without checking.
  =========================================================================

  Implements the HTTP contract backend/esp32_bridge.py and backend/main.py
  already expect:

    GET /tap   - triggers one tap-length accelerometer capture, returns an
                 HTML page with a <textarea> containing "X,Y,Z" CSV lines,
                 one per sample. This exact shape is required because
                 backend/esp32_bridge.py regex-scrapes the <textarea>.
    GET /go    - starts driving forward (duration is controlled entirely
                 by the backend calling /stop after a timed delay -- see
                 backend/esp32_bridge.py trigger_move()).
    GET /stop  - stops driving.

  Also self-measures its real sampling rate on every tap (via micros())
  and includes it in the response, instead of requiring it to be typed in
  as a guess anywhere -- see SAMPLE_RATE line in the textarea output.

  Requires: Adafruit_MPU6050, Adafruit_Sensor, Adafruit_BusIO libraries.
*/
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#include "secrets.h"  // WIFI_SSID / WIFI_PASSWORD -- copy from secrets.h.example

// ---- Pins: VERIFY against your actual wiring before flashing ----
#define PIN_MOTOR_A 25
#define PIN_MOTOR_B 26

// ---- Tap capture settings ----
#define TAP_SAMPLES     200   // samples captured per tap
#define TAP_INTERVAL_US 2000  // target microseconds between samples (~500 Hz)

Adafruit_MPU6050 mpu;
WebServer server(80);

void handleTap() {
  float xs[TAP_SAMPLES], ys[TAP_SAMPLES], zs[TAP_SAMPLES];

  unsigned long t_start = micros();
  for (int i = 0; i < TAP_SAMPLES; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    xs[i] = a.acceleration.x;
    ys[i] = a.acceleration.y;
    zs[i] = a.acceleration.z;
    unsigned long target = t_start + (unsigned long)(i + 1) * TAP_INTERVAL_US;
    while (micros() < target) { /* busy-wait for consistent spacing */ }
  }
  unsigned long t_end = micros();

  // Real measured rate, not a guess -- (samples - 1) intervals elapsed.
  float measured_hz = (TAP_SAMPLES - 1) * 1000000.0 / (float)(t_end - t_start);

  String html = "<html><body><textarea id='data'>";
  html += "# SAMPLE_RATE_HZ=" + String(measured_hz, 2) + "\n";
  for (int i = 0; i < TAP_SAMPLES; i++) {
    html += String(xs[i], 4) + "," + String(ys[i], 4) + "," + String(zs[i], 4) + "\n";
  }
  html += "</textarea></body></html>";

  server.send(200, "text/html", html);
}

void handleGo() {
  digitalWrite(PIN_MOTOR_A, HIGH);
  digitalWrite(PIN_MOTOR_B, LOW);
  server.send(200, "text/plain", "going");
}

void handleStop() {
  digitalWrite(PIN_MOTOR_A, LOW);
  digitalWrite(PIN_MOTOR_B, LOW);
  server.send(200, "text/plain", "stopped");
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_MOTOR_A, OUTPUT);
  pinMode(PIN_MOTOR_B, OUTPUT);
  digitalWrite(PIN_MOTOR_A, LOW);
  digitalWrite(PIN_MOTOR_B, LOW);

  Wire.begin();
  if (!mpu.begin()) {
    Serial.println("[ERROR] MPU6050 not found. Check wiring/I2C address.");
    while (1) { delay(1000); }
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.on("/tap", handleTap);
  server.on("/go", handleGo);
  server.on("/stop", handleStop);
  server.begin();
}

void loop() {
  server.handleClient();
}
