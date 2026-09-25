"""
esp32_bridge.py - talks to the ESP32 over HTTP: tap-sensor readings and
duration-based movement.
"""
import re
import time
import requests

TEXTAREA_RE = re.compile(r"<textarea[^>]*>(.*?)</textarea>", re.DOTALL)


class ESP32Error(Exception):
    pass


def fetch_and_parse(esp32_ip: str, trigger: bool = True, timeout: float = 10.0):
    path = "/tap" if trigger else "/"
    url = f"http://{esp32_ip}{path}"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise ESP32Error(f"Could not reach ESP32 at {url}: {e}")

    if resp.status_code != 200:
        raise ESP32Error(f"ESP32 returned HTTP {resp.status_code}")

    match = TEXTAREA_RE.search(resp.text)
    if not match:
        raise ESP32Error("No <textarea> block found in ESP32 response.")

    raw = match.group(1).strip()
    xs, ys, zs = [], [], []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(",")
        if len(parts) != 3:
            continue
        try:
            x, y, z = (float(p) for p in parts)
        except ValueError:
            continue
        xs.append(x); ys.append(y); zs.append(z)

    if not xs:
        raise ESP32Error("Parsed 0 valid samples from ESP32 response.")

    return xs, ys, zs


def _get(esp32_ip: str, path: str, timeout: float = 5.0):
    url = f"http://{esp32_ip}{path}"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise ESP32Error(f"Could not reach ESP32 at {url}: {e}")
    if resp.status_code != 200:
        raise ESP32Error(f"ESP32 returned HTTP {resp.status_code} for {path}")
    return resp


def trigger_move(esp32_ip: str, duration_ms: int):
    """Duration-based move: calls /go to start, waits duration_ms, calls
    /stop. This does NOT know real-world distance -- there are no wheel
    encoders on this robot, so the caller (backend/main.py) is responsible
    for treating duration_ms honestly and not presenting it as a distance
    unless/until a real mm-per-ms calibration measurement exists."""
    _get(esp32_ip, "/go")
    time.sleep(duration_ms / 1000.0)
    _get(esp32_ip, "/stop")