// src/options.js
document.addEventListener("DOMContentLoaded", () => {
  const serverInput = document.getElementById("serverAddress");
  const apiKeyInput = document.getElementById("apiKey");
  const saveButton = document.getElementById("saveButton");
  const status = document.getElementById("status");
  const error = document.getElementById("error");

  // Load the saved server address and API key.
  chrome.storage.sync.get(["serverAddress", "apiKey"], (data) => {
    if (data.serverAddress) {
      serverInput.value = data.serverAddress;
    }
    if (data.apiKey) {
      apiKeyInput.value = data.apiKey;
    }
  });

  // Save the server address and API key.
  saveButton.addEventListener("click", () => {
    const serverAddress = serverInput.value.trim();
    const apiKey = apiKeyInput.value.trim();

    if (!serverAddress) {
      error.textContent = "Please enter a valid server address.";
      status.textContent = "";
      return;
    }

    if (!apiKey) {
      error.textContent = "Please enter a valid API key.";
      status.textContent = "";
      return;
    }

    // Validate and extract the origin using the URL API.
    let origin;
    try {
      const url = new URL(serverAddress);
      origin = url.origin;
    } catch (e) {
      error.textContent = "Invalid server address format.";
      return;
    }

    // Create the origin pattern required by the Permissions API.
    const originPattern = origin + "/*";
    console.log("Requesting permission for:", originPattern);

    // Request the permission dynamically.
    chrome.permissions.request({ origins: [originPattern] }, (granted) => {
      if (granted) {
        // Save the configuration if permission was granted.
        chrome.storage.sync.set({ serverAddress, apiKey }, () => {
          status.textContent = "Configuration saved and permission granted!";
          error.textContent = "";
          setTimeout(() => {
            status.textContent = "";
          }, 2000);
        });
      } else {
        error.textContent = "Permission for this server was not granted.";
        status.textContent = "";
      }
    });
  });
});

