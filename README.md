# HIBIKI

HIBIKI is a small bridge inspection robot project developed for NAPROCK / PROCON 2026.

The main idea of the project is to make steel bridge inspection safer and easier.  
Instead of checking every point manually, the robot can move along a steel surface, create a small impact using a solenoid, record the vibration response, and classify the condition of the steel.

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

The backend receives three-axis vibration data:

```text
X
Y
Z
