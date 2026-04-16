// background.js

// ============================================
// CONFIGURATION - Portable across machines
// ============================================
// Load API endpoint from config file or use default
// Users can update config.json to point to different backend

let API_ENDPOINT = "http://127.0.0.1:8000"; // Default for local development

// Try to load from config.json if it exists
async function loadConfig() {
  try {
    const response = await fetch(chrome.runtime.getURL("config.json"));
    if (response.ok) {
      const config = await response.json();
      if (config.API_ENDPOINT) {
        API_ENDPOINT = config.API_ENDPOINT;
        console.log(`API Endpoint loaded from config: ${API_ENDPOINT}`);
      }
    }
  } catch (error) {
    console.log("config.json not found, using default endpoint");
  }
}

// Load config when script starts
loadConfig();

// Quick reference for manual configuration:
// Edit config.json in the extension folder:
// For local: { "API_ENDPOINT": "http://127.0.0.1:8000" }
// For remote: { "API_ENDPOINT": "http://YOUR_SERVER_IP:8000" }
// Example: { "API_ENDPOINT": "http://34.142.123.45:8000" }

// Create the context menu item once the extension is installed
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "checkDeepfake",
    title: "Check video for deepfake",
    contexts: ["page", "link", "video"]
  });
  console.log("Context menu created: 'Check video for deepfake'");
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "checkDeepfake") return;

  // Determine the correct URL (page or link)
  const videoUrl = info.linkUrl || tab?.url;
  if (!videoUrl) {
    console.error("No video URL found.");
    return;
  }

  console.log("Analyzing video:", videoUrl);

  // Open results.html in a new tab
  const newTab = await chrome.tabs.create({
    url: chrome.runtime.getURL("results.html")
  });

  // Wait for the new tab to finish loading before sending the request
  const handleTabUpdate = async (tabId, changeInfo) => {
    if (tabId === newTab.id && changeInfo.status === "complete") {
      chrome.tabs.onUpdated.removeListener(handleTabUpdate);

      try {
        // Tell the results tab to show a loading state
        chrome.tabs.sendMessage(newTab.id, {
          action: "showLoading",
          message: "Downloading and analyzing video... (This may take 15-20 minutes for full analysis)"
        });

        console.log(`Sending request to: ${API_ENDPOINT}/analyze_url`);

        // Send the video URL to your FastAPI backend
        const response = await fetch(`${API_ENDPOINT}/analyze_url`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: videoUrl })
        });

        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const data = await response.json();
        console.log("Analysis complete:", data);

        // Tell results.html to start polling for completion
        chrome.tabs.sendMessage(newTab.id, {
          action: "startPolling",
          apiEndpoint: API_ENDPOINT,
          videoPath: data.video_path,
          videoUrl: videoUrl
        });
      } catch (error) {
        console.error("Error during analysis:", error);
        chrome.tabs.sendMessage(newTab.id, {
          action: "showError",
          message: error.message || "An unknown error occurred."
        });
      }
    }
  };

  chrome.tabs.onUpdated.addListener(handleTabUpdate);
});
