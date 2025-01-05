// Fetch the saved server address
async function getServerAddress() {
  return new Promise((resolve) => {
    chrome.storage.sync.get("serverAddress", (data) => {
      resolve(data.serverAddress || "http://127.0.0.1:8000"); // Default address
    });
  });
}

// Fetch available endpoints from FastAPI
async function fetchEndpoints() {
  const serverAddress = await getServerAddress();
  const response = await fetch(`${serverAddress}/openapi.json`);
  const data = await response.json();

  // Extract endpoints
  return Object.keys(data.paths).map((path) => ({
    path,
    method: Object.keys(data.paths[path])[0] // Get HTTP method (e.g., POST)
  }));
}

// Create context menu dynamically
async function createContextMenu() {
  const endpoints = await fetchEndpoints();

  chrome.contextMenus.create({
    id: "parentMenu",
    title: "Send Selected Text",
    contexts: ["selection"]
  });

  // Create a submenu for each endpoint
  endpoints.forEach((endpoint) => {
    chrome.contextMenus.create({
      id: endpoint.path, // Use the endpoint path as the ID
      parentId: "parentMenu",
      title: endpoint.path, // Display the endpoint path
      contexts: ["selection"]
    });
  });
}

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId && info.selectionText) {
    const selectedText = info.selectionText;
    const pageUrl = tab.url; // Get the URL of the current tab
    const serverAddress = await getServerAddress();

    // Send the text and URL to the chosen endpoint
    fetch(`${serverAddress}${info.menuItemId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text: selectedText,
        url: pageUrl
      })
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(`Response from ${info.menuItemId}:`, data);
      })
      .catch((error) => {
        console.error("Error sending text:", error);
      });
  }
});

// Create the context menu when the extension is installed
chrome.runtime.onInstalled.addListener(() => {
  createContextMenu();
});

