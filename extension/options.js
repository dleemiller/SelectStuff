document.addEventListener("DOMContentLoaded", () => {
  const serverInput = document.getElementById("serverAddress");
  const saveButton = document.getElementById("saveButton");
  const status = document.getElementById("status");

  // Load the saved server address
  chrome.storage.sync.get("serverAddress", (data) => {
    if (data.serverAddress) {
      serverInput.value = data.serverAddress;
    }
  });

  // Save the server address
  saveButton.addEventListener("click", () => {
    const serverAddress = serverInput.value.trim();
    if (serverAddress) {
      chrome.storage.sync.set({ serverAddress }, () => {
        status.textContent = "Server address saved!";
        setTimeout(() => (status.textContent = ""), 2000);
      });
    } else {
      status.textContent = "Please enter a valid server address.";
    }
  });
});

