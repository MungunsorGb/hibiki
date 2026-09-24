"""
report.py - generates a PDF inspection report from collected tap points.

Honest by construction: every point included is either real ESP32 data
or explicitly labeled [SIMULATED] in its own label/method text (inherited
from main.py), so the PDF itself carries that same labeling and never
hides which points were real hardware readings vs. demo data.
"""
from datetime import datetime, timezone
from io import BytesIO
from typing import List, Dict

from fpdf import FPDF

STATUS_COLORS = {
    "Normal": (31, 157, 85),
    "Warning": (182, 120, 10),
    "Attention": (214, 60, 52),
}


def generate_pdf(points: List[Dict]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- header ---
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "HIBIKI-AI Inspection Report", ln=True)

    pdf.set_font("Helvetica", "", 10)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_text_color(110, 110, 110)
    pdf.cell(0, 6, f"Generated: {generated_at}", ln=True)
    pdf.cell(0, 6, f"Total points inspected: {len(points)}", ln=True)
    pdf.ln(4)

    # --- method disclosure, always shown, cannot be skipped ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Classification Method", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0, 5,
        "Results below use fixed, uncalibrated peak-to-peak magnitude "
        "thresholds (see backend/features.py). This is NOT a trained "
        "machine learning model. Thresholds have not been validated "
        "against real damaged specimens. Any point marked [SIMULATED] "
        "used synthetic demo data, not a real sensor reading."
    )
    pdf.ln(3)
    pdf.set_text_color(0, 0, 0)

    if not points:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(0, 8, "No inspection points recorded.", ln=True)
        buf = BytesIO()
        pdf.output(buf)
        return buf.getvalue()

    # --- summary counts ---
    counts = {"Normal": 0, "Warning": 0, "Attention": 0}
    for p in points:
        c = p.get("classification", "Normal")
        counts[c] = counts.get(c, 0) + 1

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Normal: {counts.get('Normal', 0)}   "
                   f"Warning: {counts.get('Warning', 0)}   "
                   f"Attention: {counts.get('Attention', 0)}", ln=True)
    pdf.ln(4)

    # --- table header ---
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    col_widths = [12, 45, 22, 28, 28, 55]
    headers = ["#", "Label", "Status", "Peak-Peak", "RMS", "Timestamp (UTC)"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 8, h, border=1, fill=True)
    pdf.ln()

    # --- table rows ---
    pdf.set_font("Helvetica", "", 8)
    for p in points:
        status = p.get("classification", "Normal")
        color = STATUS_COLORS.get(status, (0, 0, 0))
        summary = p.get("summary", {})

        pdf.set_text_color(0, 0, 0)
        pdf.cell(col_widths[0], 7, str(p.get("order", "") + 1 if isinstance(p.get("order"), int) else ""), border=1)
        pdf.cell(col_widths[1], 7, str(p.get("label", ""))[:28], border=1)

        pdf.set_text_color(*color)
        pdf.cell(col_widths[2], 7, status, border=1)
        pdf.set_text_color(0, 0, 0)

        pdf.cell(col_widths[3], 7, str(summary.get("peak_to_peak_magnitude", "")), border=1)
        pdf.cell(col_widths[4], 7, str(summary.get("rms_magnitude", "")), border=1)
        ts = str(p.get("timestamp_utc", ""))[:19]
        pdf.cell(col_widths[5], 7, ts, border=1)
        pdf.ln()

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()