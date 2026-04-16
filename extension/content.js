function injectButton() {
  const btn = document.createElement("button");
  btn.innerText = "Check authenticity";
  btn.className = "credibility-btn";
  btn.onclick = analyzeVideo;
  document.body.appendChild(btn);
}

async function analyzeVideo() {
  const video = document.querySelector("video");
  if (!video) return alert("No video found on this page.");

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const frames = [];
  for (let i = 0; i < 5; i++) {
    video.currentTime = (video.duration / 5) * i;
    await new Promise(r => setTimeout(r, 500));
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    frames.push(canvas.toDataURL("image/jpeg").split(",")[1]);
  }

  console.log("[CredibilityChecker] Captured", frames.length, "frames");
  chrome.runtime.sendMessage({ action: "analyzeFrames", frames, url: window.location.href }, res => {
    showOverlay(res.result, res.confidence);
  });
}

function showOverlay(result, confidence) {
  const overlay = document.createElement("div");
  overlay.className = "credibility-overlay";
  overlay.innerText = `${result} (confidence: ${confidence.toFixed(2)})`;
  document.body.appendChild(overlay);
  setTimeout(() => overlay.remove(), 6000);
}

injectButton();
