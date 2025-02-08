import { fetchEndpoints } from './api.js';

const INITIAL_RETRY_INTERVAL = 2000; // 2 seconds
const MAX_RETRY_INTERVAL = 30000; // 30 seconds
const MAX_RETRIES = 12;

let retryCount = 0;
let retryTimer = null;
let currentRetryInterval = INITIAL_RETRY_INTERVAL;

export async function createContextMenu() {
  try {
    const endpoints = await fetchEndpoints();
    console.log("[MenuManager] Fetched endpoints:", endpoints);

    // Remove existing context menus.
    chrome.contextMenus.removeAll(() => {
      if (chrome.runtime.lastError) {
        console.error("[MenuManager] Error removing context menus:", chrome.runtime.lastError);
      } else {
        console.log("[MenuManager] Existing context menus removed.");
      }
    });

    // Create parent context menu.
    chrome.contextMenus.create({
      id: "parentMenu",
      title: "Send Selected Text",
      contexts: ["selection"]
    }, () => {
      if (chrome.runtime.lastError) {
        console.error("[MenuManager] Error creating parent context menu:", chrome.runtime.lastError);
      } else {
        console.log("[MenuManager] Parent context menu created.");
      }
    });

    if (!Array.isArray(endpoints) || endpoints.length === 0) {
      // Create a default submenu if no POST endpoints are found.
      chrome.contextMenus.create({
        id: "defaultEndpoint",
        parentId: "parentMenu",
        title: "Default Endpoint",
        contexts: ["selection"]
      }, () => {
        if (chrome.runtime.lastError) {
          console.error("[MenuManager] Error creating default endpoint menu:", chrome.runtime.lastError);
        } else {
          console.log("[MenuManager] Default endpoint submenu created.");
        }
      });
      console.warn("[MenuManager] No POST endpoints found with desired tags.");
    } else {
      // Create a flat list of endpoints (no nested submenus).
      endpoints.forEach(endpoint => {
        chrome.contextMenus.create({
          id: endpoint.path,
          parentId: "parentMenu",
          title: `${endpoint.method} ${endpoint.path}`,
          contexts: ["selection"]
        }, () => {
          if (chrome.runtime.lastError) {
            console.error(`[MenuManager] Error creating menu item for ${endpoint.method} ${endpoint.path}:`, chrome.runtime.lastError);
          } else {
            console.log(`[MenuManager] Menu item for ${endpoint.method} ${endpoint.path} created.`);
          }
        });
      });
    }

    console.log("[MenuManager] Context menu created successfully.");

    // Reset retry mechanism on success.
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    retryCount = 0;
    currentRetryInterval = INITIAL_RETRY_INTERVAL;

    // Notify the user of the successful refresh.
    chrome.notifications.create({
      type: 'basic',
      iconUrl: chrome.runtime.getURL('icons/icon128.png'),
      title: 'Extension Refreshed',
      message: 'Context menu has been refreshed successfully.',
      priority: 1
    });

    return { success: true };
  } catch (error) {
    console.error("[MenuManager] Error creating context menu:", error);
    chrome.notifications.create({
      type: 'basic',
      iconUrl: chrome.runtime.getURL('icons/icon128.png'),
      title: 'Refresh Failed',
      message: `Unable to refresh context menu: ${error.message}`,
      priority: 2
    });

    // Retry with exponential backoff if needed.
    if (retryCount < MAX_RETRIES) {
      retryCount++;
      console.log(`[MenuManager] Retrying to create context menu (${retryCount}/${MAX_RETRIES}) in ${currentRetryInterval / 1000} seconds...`);
      retryTimer = setTimeout(createContextMenu, currentRetryInterval);
      currentRetryInterval = Math.min(currentRetryInterval * 2, MAX_RETRY_INTERVAL);
    } else {
      console.error("[MenuManager] Max retry attempts reached. Unable to create context menu.");
      chrome.notifications.create({
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon128.png'),
        title: 'Refresh Failed',
        message: 'Unable to refresh context menu after multiple attempts. Please ensure the backend server is running.',
        priority: 2
      });
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    return { success: false };
  }
}

