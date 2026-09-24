"""
esp32_bridge.py - talks to the ESP32 tap-sensor page and parses its data.
"""
import re
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