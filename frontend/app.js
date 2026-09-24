const API = "";

const els = {
  connBadge: document.getElementById("conn-badge"),
  esp32Ip: document.getElementById("esp32-ip"),
  btnConnect: document.getElementById("btn-connect"),
  progressText: document.getElementById("progress-text"),
  btnReset: document.getElementById("btn-reset"),
  pointLabel: document.getElementById("point-label"),
  btnTap: document.getElementById("btn-tap"),
  btnTapSim: document.getElementById("btn-tap-sim"),
  resultCard: document.getElementById("result-card"),
  resultBadge: document.getElementById("result-badge"),
  resultLabel: document.getElementById("result-label"),
  resultMethod: document.getElementById("result-method"),
  chart: document.getElementById("chart"),
  heatmapCanvas: document.getElementById("heatmap-canvas"),
  pointsList: document.getElementById("points-list"),
};

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
function dotColor(label) {
  if (label === "Normal") return "#1f9d55";
  if (label === "Warning") return "#b6780a";
  if (label === "Attention") return "#d63c34";
  return "#8a94a3";
}

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

els.btnReset.addEventListener("click", async () => {
  await fetch(`${API}/points`, { method: "DELETE" });
  els.progressText.textContent = "0 points inspected";
  els.resultCard.classList.add("hidden");
  els.pointsList.innerHTML = "";
});

function renderResult(data) {
  els.resultCard.classList.remove("hidden");
  els.resultBadge.textContent = data.classification;
  els.resultBadge.className = "badge " + badgeClass(data.classification);
  els.resultLabel.textContent = data.classification;
  els.resultMethod.textContent = data.method;
  drawChart(data.raw.x, data.raw.y, data.raw.z);
  updateProgress();
}

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
    renderResult(data);
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    els.btnTap.textContent = "Fire Tap & Inspect";
    els.btnTap.disabled = false;
  }
});

els.btnTapSim.addEventListener("click", async () => {
  const label = els.pointLabel.value.trim() || "Unlabeled point";
  const res = await fetch(`${API}/esp32/tap-sim`, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({label})
  });
  const data = await res.json();
  if (!res.ok) return alert("Error: " + (data.detail || "Failed"));
  renderResult(data);
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
  series(xs, "#e0554f");
  series(ys, "#1f9d55");
  series(zs, "#2f6fed");
}

async function updateProgress() {
  const res = await fetch(`${API}/points`);
  const data = await res.json();
  els.progressText.textContent = `${data.points.length} point(s) inspected`;
}

function drawHeatmap(points) {
  const ctx = els.heatmapCanvas.getContext("2d");
  const w = els.heatmapCanvas.width, h = els.heatmapCanvas.height;
  ctx.clearRect(0, 0, w, h);

  const y = h / 2;
  ctx.strokeStyle = "#d8dee6";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(30, y);
  ctx.lineTo(w - 30, y);
  ctx.stroke();
  ctx.fillStyle = "#8a94a3";
  ctx.font = "11px sans-serif";
  ctx.fillText("Start", 20, y + 30);
  ctx.fillText("End", w - 40, y + 30);

  const n = points.length;
  points.forEach((p, i) => {
    // Evenly spaced by tap order along the straight line.
    const frac = n === 1 ? 0.5 : i / (n - 1);
    const px = 30 + frac * (w - 60);
    ctx.beginPath();
    ctx.arc(px, y, 8, 0, Math.PI * 2);
    ctx.fillStyle = dotColor(p.classification);
    ctx.fill();
  });
}

async function loadPoints() {
  const res = await fetch(`${API}/points`);
  const data = await res.json();
  drawHeatmap(data.points);
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
        <div>#${p.order + 1} - ${p.label}</div>
        <div class="muted small">peak-to-peak: ${p.summary.peak_to_peak_magnitude}</div>
      </div>
      <span class="badge ${badgeClass(p.classification)}">${p.classification}</span>
    `;
    els.pointsList.appendChild(div);
  });
}