document.addEventListener("DOMContentLoaded", async () => {
  const companyInput = document.getElementById("company");
  const positionInput = document.getElementById("position");
  const statusSelect = document.getElementById("status");
  const apiUrlInput = document.getElementById("api-url");
  const clipBtn = document.getElementById("clip-btn");
  const statusBox = document.getElementById("status-box");

  let currentTabUrl = "";
  let currentTabDesc = "";

  // Load saved API URL
  chrome.storage?.local?.get(["apiUrl"], (res) => {
    if (res?.apiUrl) apiUrlInput.value = res.apiUrl;
  });

  // Query active tab and extract DOM info
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.id) {
      currentTabUrl = tab.url || "";
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"],
      });

      const data = results?.[0]?.result;
      if (data) {
        companyInput.value = data.company || "";
        positionInput.value = data.position || "";
        currentTabDesc = data.description || "";
      }
    }
  } catch (err) {
    console.warn("Auto-extraction failed, manual input enabled:", err);
  }

  clipBtn.addEventListener("click", async () => {
    const company = companyInput.value.trim();
    const position = positionInput.value.trim();
    const status = statusSelect.value;
    const baseUrl = apiUrlInput.value.trim().replace(/\/+$/, "");

    chrome.storage?.local?.set({ apiUrl: baseUrl });

    clipBtn.disabled = true;
    clipBtn.innerText = "Clipping...";
    statusBox.style.display = "none";

    try {
      let endpoint = `${baseUrl}/api/v1/extension/clip-job`;
      let payload = {
        company: company || "Unknown Company",
        position: position || "Unknown Position",
        status: status,
        url: currentTabUrl,
        description: currentTabDesc,
      };

      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();

      if (resp.ok) {
        statusBox.className = "status-success";
        statusBox.innerText = `Successfully clipped ${company} (${position})!`;
        statusBox.style.display = "block";
      } else {
        throw new Error(data.detail || "Failed to clip job");
      }
    } catch (err) {
      statusBox.className = "status-error";
      statusBox.innerText = `Error: ${err.message}`;
      statusBox.style.display = "block";
    } finally {
      clipBtn.disabled = false;
      clipBtn.innerText = "Clip to Job Tracker";
    }
  });
});
