// popup.js

document.addEventListener("DOMContentLoaded", () => {
  const refreshButton = document.getElementById("refreshButton");
  const statusDiv = document.getElementById("status");
  const errorDiv = document.getElementById("error");

  refreshButton.addEventListener("click", () => {
    // Clear previous messages
    statusDiv.textContent = "";
    errorDiv.textContent = "";

    // Disable the button to prevent multiple clicks
    refreshButton.disabled = true;
    refreshButton.textContent = "Refreshing...";

    // Send a message to the background script to refresh the context menu
    chrome.runtime.sendMessage({ action: "refreshContextMenu" }, (response) => {
      // Re-enable the button
      refreshButton.disabled = false;
      refreshButton.textContent = "Refresh Context Menu";

      if (chrome.runtime.lastError) {
        console.error(chrome.runtime.lastError);
        errorDiv.textContent = "Failed to send refresh request.";
        return;
      }

      if (response && response.success) {
        statusDiv.textContent = "Context menu refreshed successfully!";
      } else {
        errorDiv.textContent = "Failed to refresh context menu.";
      }
    });
  });
});
