import { createContextMenu } from './menuManager.js';
import { getServerConfig } from './api.js';

// Log as early as possible to confirm that the service worker loads.
console.log("[Background] Service worker loaded.");

// Create the context menu when the extension is installed or when the browser starts.
chrome.runtime.onInstalled.addListener(() => {
  console.log("[Background] Extension installed. Creating context menu...");
  createContextMenu();
});

chrome.runtime.onStartup.addListener(() => {
  console.log("[Background] Browser started. Creating context menu...");
  createContextMenu();
});

// Handle context menu clicks.
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  console.log("[Background] Context menu clicked.", info);
  if (info.menuItemId && info.selectionText) {
    const selectedText = info.selectionText;
    const pageUrl = tab.url;
    const { serverAddress, apiKey } = await getServerConfig();

    console.log(`[Background] Sending selected text to ${serverAddress}${info.menuItemId}`);

    try {
      const response = await fetch(`${serverAddress}${info.menuItemId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          text: selectedText,
          url: pageUrl
        })
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      const data = await response.json();
      console.log(`[Background] Response from ${info.menuItemId}:`, data);

      chrome.notifications.create({
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon128.png'),
        title: 'Send Successful',
        message: `Text sent successfully to ${info.menuItemId}.`,
        priority: 1
      });
    } catch (error) {
      console.error("[Background] Error sending text:", error);
      chrome.notifications.create({
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon128.png'),
        title: 'Send Failed',
        message: `Unable to send text: ${error.message}`,
        priority: 2
      });
    }
  }
});

// Listen for messages (e.g. when the popup requests a menu refresh)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "refreshContextMenu") {
    console.log("[Background] Received 'refreshContextMenu' message.");
    createContextMenu().then(result => {
      sendResponse(result);
    }).catch(error => {
      console.error("[Background] Error in 'refreshContextMenu':", error);
      sendResponse({ success: false });
    });
    return true; // Indicates asynchronous response.
  }
});

// Listen for keyboard commands.
chrome.commands.onCommand.addListener((command) => {
  console.log(`[Background] Command received: ${command}`);
  if (command === "refresh-context-menu") {
    createContextMenu();
  } else if (command === "open-options-page") {
    chrome.runtime.openOptionsPage();
  }
});

// Listen for changes in storage (e.g., when the serverAddress or apiKey are updated).
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "sync" && (changes.serverAddress || changes.apiKey)) {
    console.log("[Background] Server address or API key changed. Recreating context menu...");
    createContextMenu();
  }
});

