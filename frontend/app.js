const API = "";  // same origin, since backend serves this frontend

const els = {
  connBadge: document.getElementById("conn-badge"),
  esp32Ip: document.getElementById("esp32-ip"),
  btnConnect: document.getElementById("btn-connect"),
  baselineStatus: document.getElementById("baseline-status"),
  btnBaseline: document.getElementById("btn-baseline"),
  progressText: document.getElementById("progress-text"),
  btnReset: document.getElementById("btn-reset"),
  pointLabel: document.getElementById("point-label"),
  btnTap: document.getElementById("btn-tap"),
  resultCard: document.getElementById("result-card"),
  resultBadge: document.getElementById("result-badge"),
  resultLabel: document.getElementById("result-label"),
  resultDev: document.getElementById("result-dev"),
  resultMethod: document.getElementById("result-method"),
  chart: document.getElementById("chart"),
  pointsList: document.getElementById("points-list"),
};

// --- tab navigation ---
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("view-" + tab.dataset.view).classList.add("active");
    if (tab.dataset.view === "heatmap") loadPoints();
  });
});

function badgeClass(label) {
  if (label === "Normal") return "badge-normal";
  if (label === "Warning") return "badge-warning";
  if (label === "Attention") return "badge-attention";
  return "badge-gray";
}

// --- connect ---
els.btnConnect.addEventListener("click", async () => {
  const ip = els.esp32Ip.value.trim();
  if (!ip) return alert("Enter the ESP32 IP first.");
  const res = await fetch(`${API}/esp32/config`, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({esp32_ip: ip})
  });
  if (res.ok) {
    els.connBadge.textContent = "Configured";
    els.connBadge.className = "badge badge-normal";
  } else {
    els.connBadge.textContent = "Error";
    els.connBadge.className = "badge badge-attention";
  }
});

// --- baseline ---
els.btnBaseline.addEventListener("click", async () => {
  els.baselineStatus.textContent = "Firing tap for baseline...";
  try {
    const res = await fetch(`${API}/esp32/baseline`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");
    els.baselineStatus.textContent =
      `Baseline set. RMS=${data.summary.rms_magnitude}, peak-to-peak=${data.summary.peak_to_peak_magnitude}`;
  } catch (e) {
    els.baselineStatus.textContent = "Error: " + e.message;
  }
});

// --- reset ---
els.btnReset.addEventListener("click", async () => {
  await fetch(`${API}/points`, { method: "DELETE" });
  els.baselineStatus.textContent = "No baseline set yet.";
  els.progressText.textContent = "0 points inspected";
  els.resultCard.classList.add("hidden");
  els.pointsList.innerHTML = "";
});

// --- tap / inspect ---
els.btnTap.addEventListener("click", async () => {
  const label = els.pointLabel.value.trim() || "Unlabeled point";
  els.btnTap.textContent = "Tapping...";
  els.btnTap.disabled = true;
  try {
    const res = await fetch(`${API}/esp32/tap`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({label})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");

    els.resultCard.classList.remove("hidden");
    els.resultBadge.textContent = data.classification;
    els.resultBadge.className = "badge " + badgeClass(data.classification);
    els.resultLabel.textContent = data.classification;
    els.resultDev.textContent = data.deviation_pct + "%";
    els.resultMethod.textContent = data.method;

    drawChart(data.raw.x, data.raw.y, data.raw.z);
    updateProgress();
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    els.btnTap.textContent = "Fire Tap & Inspect";
    els.btnTap.disabled = false;
  }
});

function drawChart(xs, ys, zs) {
  const ctx = els.chart.getContext("2d");
  const w = els.chart.width, h = els.chart.height;
  ctx.clearRect(0, 0, w, h);
  function series(data, color) {
    const min = Math.min(...data), max = Math.max(...data);
    const range = (max - min) || 1;
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    data.forEach((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
  series(xs, "#f87171");
  series(ys, "#4ade80");
  series(zs, "#60a5fa");
}

async function updateProgress() {
  const res = await fetch(`${API}/points`);
  const data = await res.json();
  els.progressText.textContent = `${data.points.length} point(s) inspected`;
}

async function loadPoints() {
  const res = await fetch(`${API}/points`);
  const data = await res.json();
  els.pointsList.innerHTML = "";
  if (data.points.length === 0) {
    els.pointsList.innerHTML = '<p class="muted">No points inspected yet.</p>';
    return;
  }
  data.points.slice().reverse().forEach(p => {
    const div = document.createElement("div");
    div.className = "point-item";
    div.innerHTML = `
      <div>
        <div>${p.label}</div>
        <div class="muted small">${p.deviation_pct}% deviation</div>
      </div>
      <span class="badge ${badgeClass(p.classification)}">${p.classification}</span>
    `;
    els.pointsList.appendChild(div);
  });
}