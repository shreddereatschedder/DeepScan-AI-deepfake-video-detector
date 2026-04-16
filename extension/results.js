// results.js - cleaned and fixed

const loadingSection = document.getElementById("loading");
const resultsSection = document.getElementById("results");
const errorSection = document.getElementById("error");
const statusText = document.getElementById("status-text");
const loadingMessage = document.getElementById("loading-message");
const errorMessage = document.getElementById("error-message");
const videoTitle = document.getElementById("video-title");
const videoPath = document.getElementById("video-path");
const videoFrame = document.getElementById("video-frame");
const videoOpen = document.getElementById("video-open");
const gaugeFill = document.getElementById("gauge-fill");
const gaugeScore = document.getElementById("gauge-score");
const gaugeLabel = document.getElementById("gauge-label");
const factorList = document.getElementById("factor-list");
const timelineChart = document.getElementById("timeline-chart");
const timelineTooltip = document.getElementById("timeline-tooltip");
const heatmap = document.getElementById("heatmap");
const networkCanvas = document.getElementById("network-canvas");

const closeReportButton = document.getElementById("close-report");
const retryButton = document.getElementById("retry");

let pollingInterval = null;
let lastVideoUrl = "";
let networkAnimationId = null;
let networkNodes = [];
let currentApiEndpoint = null;
let currentVideoPath = null;

function startNetworkCanvas() {
  if (!networkCanvas) return;
  const ctx = networkCanvas.getContext("2d");
  if (!ctx) return;

  const nodeCount = 60;
  const connectionDistance = 150;

  const resize = () => {
    networkCanvas.width = window.innerWidth;
    networkCanvas.height = window.innerHeight;
  };

  resize();

  if (!networkNodes.length) {
    networkNodes = Array.from({ length: nodeCount }, () => ({
      x: Math.random() * networkCanvas.width,
      y: Math.random() * networkCanvas.height,
      vx: (Math.random() - 0.5) * 0.6,
      vy: (Math.random() - 0.5) * 0.6,
      radius: Math.random() * 2 + 1,
    }));
  }

  const animate = () => {
    ctx.clearRect(0, 0, networkCanvas.width, networkCanvas.height);

    networkNodes.forEach((node) => {
      node.x += node.vx;
      node.y += node.vy;

      if (node.x < 0 || node.x > networkCanvas.width) node.vx *= -1;
      if (node.y < 0 || node.y > networkCanvas.height) node.vy *= -1;
    });

    for (let i = 0; i < networkNodes.length; i += 1) {
      for (let j = i + 1; j < networkNodes.length; j += 1) {
        const dx = networkNodes[i].x - networkNodes[j].x;
        const dy = networkNodes[i].y - networkNodes[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < connectionDistance) {
          const opacity = (1 - distance / connectionDistance) * 0.18;
          const isPink = (i + j) % 7 === 0;
          ctx.beginPath();
          ctx.moveTo(networkNodes[i].x, networkNodes[i].y);
          ctx.lineTo(networkNodes[j].x, networkNodes[j].y);
          ctx.strokeStyle = isPink
            ? `rgba(255, 45, 120, ${opacity})`
            : `rgba(0, 232, 123, ${opacity})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }

    networkNodes.forEach((node) => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 232, 123, 0.45)";
      ctx.fill();

      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius + 2, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 232, 123, 0.08)";
      ctx.fill();
    });

    networkAnimationId = window.requestAnimationFrame(animate);
  };

  if (!networkAnimationId) {
    window.addEventListener("resize", resize, { passive: true });
    animate();
  }
}

function stopNetworkCanvas() {
  if (networkAnimationId) {
    window.cancelAnimationFrame(networkAnimationId);
    networkAnimationId = null;
  }
}

function showLoading(message) {
  if (loadingSection) loadingSection.classList.remove("hidden");
  if (resultsSection) resultsSection.classList.add("hidden");
  if (errorSection) errorSection.classList.add("hidden");
  if (statusText) statusText.textContent = "Analyzing";
  if (loadingMessage) loadingMessage.textContent = message || "Analyzing video...";
  startNetworkCanvas();
}

function showError(message) {
  if (loadingSection) loadingSection.classList.add("hidden");
  if (resultsSection) resultsSection.classList.add("hidden");
  if (errorSection) errorSection.classList.remove("hidden");
  if (statusText) statusText.textContent = "Error";
  if (errorMessage) errorMessage.textContent = message || "Something went wrong.";
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
  stopNetworkCanvas();
}

function setGauge(score) {
  const clamped = Math.max(0, Math.min(score, 100));
  let primaryColor = '#ffb800';
  if (clamped >= 60) primaryColor = '#ff2d78';
  else if (clamped < 30) primaryColor = '#00e87b';
  const endAngle = (clamped / 100) * 360;
  let gradient;
  if (endAngle <= 108) {
    gradient = `conic-gradient(from 0deg, #00e87b 0deg ${endAngle}deg, transparent ${endAngle}deg, transparent 360deg)`;
  } else if (endAngle <= 216) {
    gradient = `conic-gradient(from 0deg, #00e87b 0deg 108deg, #ffb800 108deg, #ffb800 ${endAngle}deg, transparent ${endAngle}deg, transparent 360deg)`;
  } else {
    gradient = `conic-gradient(from 0deg, #00e87b 0deg 108deg, #ffb800 108deg, #ffb800 216deg, #ff2d78 216deg, #ff2d78 ${endAngle}deg, transparent ${endAngle}deg, transparent 360deg)`;
  }
  if (gaugeFill) gaugeFill.style.background = gradient;
  if (gaugeFill) gaugeFill.style.filter = `drop-shadow(0 0 12px ${primaryColor}80)`;
  if (gaugeScore) gaugeScore.textContent = `${clamped.toFixed(0)}%`;
  if (gaugeLabel) {
    if (clamped >= 60) gaugeLabel.textContent = "High risk";
    else if (clamped >= 30) gaugeLabel.textContent = "Moderate risk";
    else gaugeLabel.textContent = "Low risk";
  }
}

function renderFactors(data) {
  if (!factorList) return;
  factorList.innerHTML = "";

  if (!data || !data.summary) {
    factorList.innerHTML = "<li class='factor'><div class='factor-content'><div class='factor-title'>No factors available</div></div></li>";
    return;
  }

  const summary = data.summary;
  const metrics = summary.forensic_metrics || {};

  const METRIC_DEFS = {
    warp_score: { label: "Warping Artifacts", explain: "Detected geometric warping in facial regions.", thresh: 0.05 },
    lighting_score: { label: "Lighting Inconsistency", explain: "Frame-to-frame lighting inconsistency detected.", thresh: 0.05 },
    texture_score: { label: "Texture Anomalies", explain: "Unnatural texture or blending artifacts in skin regions.", thresh: 0.05 },
    flicker_score: { label: "Temporal Flicker", explain: "Abrupt inter-frame flicker or temporal instability.", thresh: 0.05 },
    forensic_score: { label: "Aggregate Forensic Score", explain: "Combined forensic signal indicating manipulation likelihood.", thresh: 0.05 },
    frequency_score: { label: "Frequency Artifacts", explain: "Hidden frequency-domain artefacts.", thresh: 0.05 },
    chrominance_score: { label: "Chrominance", explain: "Colour/edge chrominance anomalies.", thresh: 0.05 },
    compression_score: { label: "Compression Artifacts", explain: "Signs of repeated compression.", thresh: 0.05 },
  };

  const DETAILS = {
    warp_score: "The face appears to bend, stretch, or warp unnaturally - a common sign that AI has been used to overlay or reshape a face in the video.",
    lighting_score: "The light and shadows on the face don't match the rest of the scene. In a real video, lighting falls consistently - mismatches suggest the face may have been added or altered.",
    texture_score: "The skin on the face looks unnaturally smooth or blurry compared to the rest of the video. AI face-swap tools often erase natural skin texture like pores and fine lines.",
    flicker_score: "The face appears to slightly flicker or change between frames in a way that wouldn't happen naturally. This can occur when an AI model generates each frame independently without keeping them consistent.",
    frequency_score: "Hidden patterns have been found in the image data that are invisible to the naked eye but are a known fingerprint left behind by AI image generators. Think of it like a watermark only a detector can see.",
    chrominance_score: "The skin colour around the edges of the face - such as near the hairline, ears, or jawline - doesn't blend naturally with the surroundings. This 'cut-out' effect is a common sign of a face that has been digitally pasted onto another body.",
    compression_score: "The video shows signs of having been saved and compressed more than once, which is typical when a manipulated video is exported and re-uploaded. While not conclusive alone, it often accompanies other signs of editing.",
  };

  const deriveKeyFromLabel = (label) => {
    if (!label) return null;
    const l = String(label).toLowerCase();
    if (l.includes('light')) return 'lighting_score';
    if (l.includes('texture') || l.includes('skin')) return 'texture_score';
    if (l.includes('flicker') || l.includes('temporal')) return 'flicker_score';
    if (l.includes('frequency')) return 'frequency_score';
    if (l.includes('chromin')) return 'chrominance_score';
    if (l.includes('compress')) return 'compression_score';
    if (l.includes('warp')) return 'warp_score';
    return null;
  };

  const entries = Object.keys(metrics)
    .filter((k) => k in METRIC_DEFS)
    .map((k) => ({ key: k, value: Number(metrics[k] || 0), def: METRIC_DEFS[k] }))
    .filter((e) => !Number.isNaN(e.value));

  const metricItems = entries.map((e) => {
    const score = Math.max(0, Math.min(1, e.value));
    const severity = score >= 0.7 ? 'high' : score >= 0.4 ? 'medium' : 'low';
    return { key: e.key, label: e.def.label, explain: e.def.explain, score, severity, def: e.def };
  });

  let displayItems = metricItems.slice();

  if (Array.isArray(summary.forensic_factors)) {
    for (const f of summary.forensic_factors) {
      const label = f.label || f.name || 'Forensic Signal';
      const lowerLabel = String(label).toLowerCase();
      if (lowerLabel.includes('alignment') || (f.key && f.key === 'alignment_score')) {
        continue;
      }
      const sev = String(f.severity || '').toLowerCase() || 'low';
      const derived = f.key || deriveKeyFromLabel(label) || null;
      const score = (typeof f.score === 'number') ? f.score : undefined;
      const exists = displayItems.some((d) => (d.key && derived && d.key === derived) || (d.label && String(d.label).toLowerCase() === String(label).toLowerCase()));
      if (!exists) {
        displayItems.push({ key: derived, label, explain: f.description || f.reason || '', score, severity: sev });
      }
    }
  }

  const severityOrder = { high: 0, medium: 1, low: 2 };
  displayItems.sort((a, b) => {
    const ra = severityOrder[String(a.severity || 'low')] ?? 2;
    const rb = severityOrder[String(b.severity || 'low')] ?? 2;
    if (ra !== rb) return ra - rb;
    const sa = (typeof a.score === 'number') ? a.score : -1;
    const sb = (typeof b.score === 'number') ? b.score : -1;
    if (sa !== sb) return sb - sa;
    return String(b.label || '').localeCompare(String(a.label || '')) * -1;
  });

  if (displayItems.length === 0) {
    if (Array.isArray(summary.forensic_factors) && summary.forensic_factors.length > 0) {
      for (const factor of summary.forensic_factors) {
        const label = factor.label || factor.name || '';
        const lowerLabel = String(label).toLowerCase();
        if (lowerLabel.includes('alignment') || (factor.key && factor.key === 'alignment_score')) {
          continue;
        }
        const li = document.createElement('li');
        li.className = 'factor';
        li.setAttribute('data-severity', factor.severity || 'low');
        li.innerHTML = `
          <div class="factor-icon">${(factor.icon || 'FX').slice(0, 2).toUpperCase()}</div>
          <div class="factor-content">
            <div class="factor-header">
              <div class="factor-title">${factor.label || factor.name || 'Forensic Signal'}</div>
              <span class="factor-badge">${(factor.severity || 'low').toUpperCase()}</span>
            </div>
            <div class="factor-desc">${factor.description || factor.reason || 'No details provided'}</div>
          </div>
        `;
        factorList.appendChild(li);
      }
      return;
    }
    factorList.innerHTML = "<li class='factor'><div class='factor-content'><div class='factor-title'>No significant forensic signals detected</div></div></li>";
    return;
  }

  function updateFactorsMaxHeight() {
    try {
      const chart = document.querySelector('.card.factor-card .timeline-chart') || document.getElementById('timeline-chart');
      const factorsSection = document.querySelector('.score-card .factors-section');
      if (!chart || !factorsSection) return;
      const chartBottom = chart.getBoundingClientRect().bottom;
      const factorsTop = factorsSection.getBoundingClientRect().top;
      let maxH = Math.floor(chartBottom - factorsTop - 12);
      if (maxH < 80) maxH = 80;
      factorsSection.style.maxHeight = `${maxH}px`;
      factorsSection.style.overflowY = 'auto';
    } catch (err) { /* ignore */ }
  }

  if (!window.__rc_factors_resize_bound) {
    window.__rc_factors_resize_bound = true;
    let __rc_resize_timer = null;
    window.addEventListener('resize', () => {
      if (__rc_resize_timer) clearTimeout(__rc_resize_timer);
      __rc_resize_timer = setTimeout(() => {
        updateFactorsMaxHeight();
        __rc_resize_timer = null;
      }, 140);
    }, { passive: true });
    document.addEventListener('DOMContentLoaded', () => setTimeout(updateFactorsMaxHeight, 200));
  }

  for (const entry of displayItems) {
    const percent = (typeof entry.score === 'number') ? `${(entry.score * 100).toFixed(1)}%` : '';
    const abbr = (entry.label || 'FX').split(/\s+/).map(w => w[0]||'').join('').slice(0,2).toUpperCase();
    const detailsKey = entry.key || deriveKeyFromLabel(entry.label || '');
    const extra = DETAILS[detailsKey] || '';
    const li = document.createElement('li');
    li.className = 'factor';
    li.setAttribute('data-severity', entry.severity || 'low');
    li.innerHTML = `
      <div class="factor-icon">${abbr}</div>
      <div class="factor-content">
        <div class="factor-header">
          <div class="factor-title">${entry.label}</div>
          <div class="factor-controls">
            <span class="factor-badge">${(entry.severity || 'low').toUpperCase()}</span>
            <button class="factor-toggle" aria-expanded="false" title="Show details">▾</button>
          </div>
        </div>
        <div class="factor-desc">${entry.explain || ''}${percent ? ` (${percent})` : ''}</div>
        <div class="factor-details" aria-hidden="true">${extra}</div>
      </div>
    `;
    factorList.appendChild(li);
    const toggle = li.querySelector('.factor-toggle');
    const details = li.querySelector('.factor-details');
    if (toggle && details) {
      toggle.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const open = toggle.getAttribute('aria-expanded') === 'true';
        if (open) {
          toggle.setAttribute('aria-expanded', 'false');
          details.classList.remove('open');
          toggle.classList.remove('open');
          details.setAttribute('aria-hidden', 'true');
        } else {
          const otherToggles = factorList.querySelectorAll('.factor-toggle.open');
          otherToggles.forEach((t) => {
            if (t === toggle) return;
            t.setAttribute('aria-expanded', 'false');
            t.classList.remove('open');
            const parent = t.closest('.factor');
            if (parent) {
              const d = parent.querySelector('.factor-details');
              if (d) { d.classList.remove('open'); d.setAttribute('aria-hidden', 'true'); }
            }
          });
          const otherDetails = factorList.querySelectorAll('.factor-details.open');
          otherDetails.forEach((d) => {
            if (d === details) return;
            d.classList.remove('open');
            d.setAttribute('aria-hidden', 'true');
            const p = d.closest('.factor');
            if (p) {
              const t = p.querySelector('.factor-toggle');
              if (t) { t.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); }
            }
          });
          toggle.setAttribute('aria-expanded', 'true');
          details.classList.add('open');
          toggle.classList.add('open');
          details.setAttribute('aria-hidden', 'false');
        }
      });
    }
  }

  setTimeout(() => { try { updateFactorsMaxHeight(); } catch (e) { /* ignore */ } }, 60);
}

function extractVideoId(url) {
  if (!url) return null;
  const patterns = [
    /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
    /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /^([a-zA-Z0-9_-]{11})$/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

function renderVideo(url) {
  const videoId = extractVideoId(url);
  if (!videoId) {
    if (videoFrame) videoFrame.innerHTML = `<div class="video-placeholder">No preview available</div>`;
    if (videoOpen) videoOpen.setAttribute("href", "#");
    return;
  }
  const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
  if (videoOpen) videoOpen.setAttribute("href", watchUrl);
  if (videoFrame) videoFrame.innerHTML = `
    <a class="video-thumb" href="${watchUrl}" target="_blank" rel="noopener">
      <img src="https://i.ytimg.com/vi/${videoId}/hqdefault.jpg" alt="Video thumbnail" />
      <span class="play-icon">▶</span>
    </a>
  `;
}

function renderTimeline(data) {
  if (!timelineChart) return;
  if (!data || !data.summary) {
    timelineChart.innerHTML = `<p>No factor data available</p>`;
    return;
  }
  const summary = data.summary;
  const metrics = summary.forensic_metrics || {};
  const AXES = [
    { key: 'warp_score', label: 'Warping Artifacts' },
    { key: 'lighting_score', label: 'Lighting Inconsistency' },
    { key: 'texture_score', label: 'Texture Anomalies' },
    { key: 'flicker_score', label: 'Temporal Flicker' },
    { key: 'frequency_score', label: 'Frequency Artifacts' },
    { key: 'chrominance_score', label: 'Chrominance' },
    { key: 'compression_score', label: 'Compression Artifacts' },
  ];
  const values = AXES.map(a => Math.max(0, Math.min(1, Number(metrics[a.key] || 0))));
  const width = 340, height = 120, leftPad = 40, rightPad = 15, topPad = 25, bottomPad = 30;
  const usableWidth = width - leftPad - rightPad, usableHeight = height - topPad - bottomPad;
  const barCount = AXES.length, barGap = 12;
  const barHeight = Math.floor((usableHeight - (barGap * (barCount - 1))) / barCount);
  const colorMap = {
    high: { fill: 'rgba(255,45,120,0.5)', stroke: 'rgba(255, 45, 120, 0.45)', text: '#ff6b9a' },
    medium: { fill: 'rgba(255,199,0,0.45)', stroke: 'rgba(255, 199, 0, 0.35)', text: '#ffd166' },
    low: { fill: 'rgba(0,232,123,0.4)', stroke: 'rgba(0, 232, 123, 0.35)', text: '#6ef3b6' }
  };
  const ticks = [0,20,40,60,80,100];
  const bars = AXES.map((a,i) => {
    const v = values[i];
    const percent = Math.round(v * 1000) / 10;
    const barW = Math.round((v * usableWidth));
    const severity = v >= 0.7 ? 'high' : v >= 0.4 ? 'medium' : 'low';
    const palette = colorMap[severity] || colorMap.low;
    return { label: a.label, percent, fill: palette.fill, stroke: palette.stroke, text: palette.text };
  });
  const barWidth = Math.floor((usableWidth - (barGap * (bars.length - 1))) / bars.length);
  const barsVert = bars.map((b,i) => {
    const x = leftPad + i * (barWidth + barGap);
    const barH = Math.round((b.percent / 100) * usableHeight);
    const y = topPad + (usableHeight - barH);
    return { x, y, barW: barWidth, barH, label: AXES[i].label, fill: b.fill, stroke: b.stroke, text: b.text, percent: b.percent };
  });
  const abbrFor = (label) => { if (!label) return ''; const parts = String(label).split(/\s+/).map(w => w[0] || ''); return parts.join('').slice(0, 2).toUpperCase(); };
  const svg = `
    <svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img" aria-label="Forensic factors vertical chart">
      <style>
        .axis-text { fill: #ffffff; font-size: 9px; font-weight:600; }
        .tick-text { fill: #ffffff; font-size: 10px; }
        .percent-text { fill: #9aa6b2; font-size: 10px; font-weight:600; }
      </style>
      <g stroke="#1f2937" stroke-opacity="0.15" stroke-width="1.5">
        ${ticks.map(t=>{ const y = topPad + Math.round((1 - t/100) * usableHeight); return `<line x1="${leftPad}" y1="${y}" x2="${leftPad+usableWidth}" y2="${y}" />`; }).join('')}
      </g>
      <g>
        ${ticks.map(t=>{ const y = topPad + Math.round((1 - t/100) * usableHeight); return `<text x="${leftPad-12}" y="${y+5}" class="tick-text" text-anchor="end">${t}%</text>`; }).join('')}
      </g>
      ${barsVert.map((b,i)=>`
        <rect x="${b.x}" y="${b.y}" width="${b.barW}" height="${b.barH}" rx="8" fill="${b.fill}" stroke="${b.stroke}" stroke-width="1.6" data-label="${b.label}"></rect>
        <text x="${b.x + b.barW/2}" y="${b.y - 10}" class="percent-text" text-anchor="middle" fill="${b.text || '#9aa6b2'}">${b.percent}%</text>
        <text x="${b.x + b.barW/2}" y="${topPad + usableHeight + 26}" class="axis-text" text-anchor="middle">${abbrFor(b.label)}</text>
      `).join('')}
    </svg>
  `;
  timelineChart.innerHTML = svg;
  try { setTimeout(() => { if (typeof setupBarTooltips === 'function') setupBarTooltips(); }, 50); } catch (e) { /* ignore */ }
}

function ensureBarTooltip(){
  let t = document.getElementById('bar-tooltip');
  if(!t){
    t = document.createElement('div');
    t.id = 'bar-tooltip';
    t.className = 'bar-tooltip';
    t.setAttribute('aria-hidden','true');
    document.body.appendChild(t);
  }
  return t;
}

function setupBarTooltips(){
  const tooltip = ensureBarTooltip();
  const offset = 12;
  const bars = document.querySelectorAll('.timeline-chart svg rect[data-label], .timeline-chart svg rect[data-factor]');
  if(!bars || bars.length === 0) return;
  bars.forEach(bar => {
    const label = bar.dataset.label || bar.getAttribute('data-label') || '';
    const onEnter = (e) => { tooltip.textContent = label || ''; tooltip.classList.add('visible'); tooltip.setAttribute('aria-hidden','false'); };
    const onMove = (e) => {
      let left = e.clientX + offset; let top = e.clientY + offset;
      tooltip.style.left = left + 'px'; tooltip.style.top = top + 'px';
      const r = tooltip.getBoundingClientRect();
      if (r.right > window.innerWidth) tooltip.style.left = (e.clientX - r.width - offset) + 'px';
      if (r.bottom > window.innerHeight) tooltip.style.top = (e.clientY - r.height - offset) + 'px';
    };
    const onLeave = () => { tooltip.classList.remove('visible'); tooltip.setAttribute('aria-hidden','true'); };
    if (bar._tooltipHandlers){
      bar.removeEventListener('mouseenter', bar._tooltipHandlers.enter);
      bar.removeEventListener('mousemove', bar._tooltipHandlers.move);
      bar.removeEventListener('mouseleave', bar._tooltipHandlers.leave);
    }
    bar._tooltipHandlers = { enter: onEnter, move: onMove, leave: onLeave };
    bar.addEventListener('mouseenter', onEnter);
    bar.addEventListener('mousemove', onMove);
    bar.addEventListener('mouseleave', onLeave);
  });
}

function renderHeatmap(data) {
  if (!heatmap) return;
  heatmap.innerHTML = "";
  if (!data || !data.summary) { heatmap.innerHTML = "<p>No heatmap data available</p>"; return; }
  const summary = data.summary;
  const fakeFrames = summary.fake_frames || 0;
  const totalFrames = summary.total_frames_analyzed || 1;
  const stats = [
    { label: "Real frames", value: summary.total_frames_analyzed - fakeFrames, color: "#00e87b" },
    { label: "Fake frames", value: fakeFrames, color: "#ff2d78" },
    { label: "Frame coverage", value: `${(totalFrames / 30).toFixed(1)}s approx`, color: "#00a8e8" },
  ];
  stats.forEach((stat) => {
    const cell = document.createElement("div");
    cell.className = "heatmap-cell";
    cell.style.borderLeft = `4px solid ${stat.color}`;
    cell.innerHTML = `<span style="color: ${stat.color}; font-weight: 600;">${stat.label}</span>: ${stat.value}`;
    heatmap.appendChild(cell);
  });
}

function showResults(data) {
  if (loadingSection) loadingSection.classList.add("hidden");
  if (errorSection) errorSection.classList.add("hidden");
  if (resultsSection) resultsSection.classList.remove("hidden");
  if (statusText) statusText.textContent = "Complete";
  if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
  stopNetworkCanvas();
  const analysis = data.analysis || {};
  const summary = data.summary || {};
  const fakePercent = typeof summary.fake_percentage === 'number' ? summary.fake_percentage : 0;
  const score = fakePercent;
  const title = analysis.video_title || data.video_title || "Analysis Result";
  videoTitle && (videoTitle.textContent = title);
  if (videoPath) videoPath.style.display = 'none';
  renderVideo(lastVideoUrl);
  if (summary.fake_percentage === undefined && analysis.confidence === undefined) {
    if (gaugeScore) gaugeScore.textContent = "--%";
    if (gaugeLabel) gaugeLabel.textContent = "Pending";
    if (gaugeFill) gaugeFill.style.transform = "rotate(-90deg)";
    renderFactors(null); renderTimeline(null); renderHeatmap(null);
  } else {
    setGauge(score); renderFactors(data); renderTimeline(data); renderHeatmap(data);
  }
}

function normalizeStatusPayload(payload) {
  if (!payload || !payload.summary) return { analysis: {}, summary: {} };
  const summary = payload.summary;
  return {
    video_path: payload.video_path,
    summary: summary,
    analysis: {
      confidence: (typeof summary.fake_percentage === 'number') ? summary.fake_percentage : 0,
      is_deepfake: summary.overall_label === "fake" || (typeof summary.fake_percentage === 'number' && summary.fake_percentage > 50),
      notes: `Fake frames: ${summary.fake_frames} of ${summary.total_frames_analyzed}`,
      video_title: payload.video_path ? payload.video_path.split(/[\\\/]/).pop() : "Analysis Result",
    },
    message: "Analysis complete",
  };
}

async function pollStatus(apiEndpoint, videoPathParam) {
  const url = `${apiEndpoint}/analysis_status?video_path=${encodeURIComponent(videoPathParam)}`;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Status check failed: ${response.status}`);
    const data = await response.json();
    if (data.status === "done") { showResults(normalizeStatusPayload(data)); return; }
    if (data.status === "error") { showError(data.error || "Analysis failed."); }
  } catch (error) {
    showError(error.message || "Failed to fetch analysis status.");
  }
}

if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.action === "showLoading") showLoading(message.message);
    if (message.action === "showResults") showResults(message.data || {});
    if (message.action === "startPolling") {
      const apiEndpoint = message.apiEndpoint;
      const videoPathMsg = message.videoPath;
      lastVideoUrl = message.videoUrl || "";
      currentApiEndpoint = apiEndpoint || currentApiEndpoint;
      currentVideoPath = videoPathMsg || currentVideoPath;
      if (!apiEndpoint || !videoPathMsg) { showError("Missing analysis details for polling."); return; }
      showLoading("Processing frames. This may take a few minutes...");
      pollStatus(apiEndpoint, videoPathMsg);
      pollingInterval = setInterval(() => { pollStatus(apiEndpoint, videoPathMsg); }, 5000);
    }
    if (message.action === "showError") showError(message.message);
  });
}

if (closeReportButton) {
  closeReportButton.addEventListener("click", async () => {
    const api = (typeof currentApiEndpoint !== 'undefined' && currentApiEndpoint) || window.__API_ENDPOINT__ || 'http://127.0.0.1:8000';
    try { await fetch(`${api}/cleanup_results`, { method: 'POST' }); } catch (err) { console.warn('Cleanup request failed', err); }
    try { window.close(); } catch (e) { /* ignore */ }
  });
}

if (retryButton) {
  retryButton.addEventListener("click", () => {
    try { window.close(); } catch (e) { /* ignore */ }
  });
}
