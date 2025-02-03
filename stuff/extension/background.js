  // background.js

  // Define retry parameters for exponential backoff
  const INITIAL_RETRY_INTERVAL = 2000; // 2 seconds
  const MAX_RETRY_INTERVAL = 30000; // 30 seconds
  const MAX_RETRIES = 12; // Total number of retries

  let retryCount = 0;
  let retryTimer = null;
  let currentRetryInterval = INITIAL_RETRY_INTERVAL;

  // Define desired tags to display in the context menu
  // const DESIRED_TAGS = ["News", "FTS", "Database"];
  const DESIRED_TAGS = ["Select/"];

  // Utility function to delay execution
  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Fetch the saved server address and API key
  async function getServerConfig() {
    try {
      const data = await chrome.storage.sync.get(["serverAddress", "apiKey"]);
      return {
        serverAddress: data.serverAddress || "http://localhost:8000",
        apiKey: data.apiKey || ""
      };
    } catch (error) {
      console.error("Failed to retrieve server configuration:", error);
      // Optionally, notify the user or fallback to defaults
      return {
        serverAddress: "http://127.0.0.1:8000",
        apiKey: ""
      };
    }
  }


  async function fetchEndpoints() {
    const { serverAddress, apiKey } = await getServerConfig();
    
    console.log('Attempting to fetch endpoints with config:', {
      serverAddress,
      hasApiKey: !!apiKey
    });

    try {
      // Try root endpoint first
      const rootCheck = await fetch(`${serverAddress}/`);
      console.log('Root endpoint check:', {
        ok: rootCheck.ok,
        status: rootCheck.status
      });

      // Then health check
      const healthCheck = await fetch(`${serverAddress}/health`, {
        method: 'GET',
        mode: 'cors',
        credentials: 'omit',
        headers: {
          'Accept': 'application/json'
        }
      });
      console.log('Health check response:', {
        ok: healthCheck.ok,
        status: healthCheck.status
      });

      // Then fetch the OpenAPI schema
      const response = await fetch(`${serverAddress}/openapi.json `, {
        method: 'GET',
        mode: 'cors',
        credentials: 'omit',
        headers: {
          'Accept': 'application/json'
        }
      });

      console.log('OpenAPI response headers:', {
        cors: response.headers.get('access-control-allow-origin'),
        contentType: response.headers.get('content-type')
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response body:', errorText);
        throw new Error(`Failed to fetch openapi.json: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('OpenAPI schema paths:', Object.keys(data.paths));

      // Process endpoints...
      const postEndpoints = [];
      for (const path in data.paths) {
        const methods = data.paths[path];
        console.log(`Examining path ${path}:`, methods);

        for (const method in methods) {
          if (method.toLowerCase() === "post") {
            const endpointInfo = methods[method];
            console.log(`Found POST endpoint at ${path}:`, endpointInfo);
            
            const endpoint = {
              path,
              method: method.toUpperCase(),
              tags: endpointInfo.tags || []
            };

            console.log(`Endpoint tags:`, endpoint.tags);
            const hasDesiredTag = endpoint.tags.some(tag => 
              DESIRED_TAGS.some(desiredTag => tag.startsWith(desiredTag))
            );
            console.log(`Has desired tag (${DESIRED_TAGS.join(', ')}):`, hasDesiredTag);

            if (hasDesiredTag) {
              postEndpoints.push(endpoint);
            }
          }
        }
      }

      console.log('Final filtered endpoints:', postEndpoints);
      return postEndpoints;

    } catch (error) {
      console.error('Detailed error in fetchEndpoints:', {
        message: error.message,
        stack: error.stack,
        serverAddress,
        type: error.name
      });
      throw error;
    }
  }

  function getRouteStructure(path) {
    // Split path and remove empty parts
    const parts = path.split('/').filter(part => part.length > 0);
    
    // Create nested structure recursively
    function createNestedStructure(currentParts, parentPath = '') {
      if (currentParts.length === 0) return null;

      const currentPart = currentParts[0];
      const newPath = parentPath + '/' + currentPart;
      
      return {
        name: currentPart.charAt(0).toUpperCase() + currentPart.slice(1),
        fullPath: newPath,
        children: currentParts.length > 1 ? createNestedStructure(currentParts.slice(1), newPath) : null
      };
    }

    return createNestedStructure(parts);
  }

  function parseHierarchicalTag(tag) {
    // Split the tag into parts (e.g., "Select/News" -> ["Select", "News"])
    return tag.split('/').filter(part => part.length > 0);
  
  }
  function categorizeEndpoints(endpoints) {
    const menuStructure = {};

    endpoints.forEach(endpoint => {
      let currentLevel = menuStructure;
      const structure = getRouteStructure(endpoint.path);
      
      // Helper function to traverse/create the path
      function buildMenuPath(node) {
        if (!node) return;

        const categoryName = node.name;
        
        // Create category if it doesn't exist
        if (!currentLevel[categoryName]) {
          currentLevel[categoryName] = {
            path: node.fullPath,
            items: [],
            subcategories: {}
          };
        }

        // If we're at the leaf node, add the endpoint
        if (!node.children) {
          currentLevel[categoryName].items.push(endpoint);
        } else {
          // Move to next level
          currentLevel = currentLevel[categoryName].subcategories;
          buildMenuPath(node.children);
        }
      }

      buildMenuPath(structure);
    });

    return menuStructure;
  }

  // Remove existing context menus to prevent duplicates
  function removeExistingContextMenus() {
    chrome.contextMenus.removeAll(() => {
      if (chrome.runtime.lastError) {
        console.error("Error removing context menus:", chrome.runtime.lastError);
      } else {
        console.log("Existing context menus removed.");
      }
    });
  }

  // Create context menu dynamically with categorized POST endpoints
  async function createContextMenu() {
    try {
      const endpoints = await fetchEndpoints();

      // Remove existing context menus
      removeExistingContextMenus();

      // Create parent context menu
      chrome.contextMenus.create({
        id: "parentMenu",
        title: "Send Selected Text",
        contexts: ["selection"]
      }, () => {
        if (chrome.runtime.lastError) {
          console.error("Error creating parent context menu:", chrome.runtime.lastError);
        } else {
          console.log("Parent context menu created.");
        }
      });

      if (endpoints.length === 0) {
        // Create a default submenu if no POST endpoints are found
        chrome.contextMenus.create({
          id: "defaultEndpoint",
          parentId: "parentMenu",
          title: "Default Endpoint",
          contexts: ["selection"]
        }, () => {
          if (chrome.runtime.lastError) {
            console.error("Error creating default endpoint menu:", chrome.runtime.lastError);
          } else {
            console.log("Default endpoint submenu created.");
          }
        });
        console.warn("No POST endpoints found with desired tags.");
      } else {
        // Categorize endpoints with our new dynamic categorization
        const categorized = categorizeEndpoints(endpoints);

        // Recursive function to create menu items
        function createMenuItems(categories, parentId) {
          for (const categoryName in categories) {
            const category = categories[categoryName];
            const categoryId = `menu_${category.path || categoryName}`;

            // Create category menu item
            chrome.contextMenus.create({
              id: categoryId,
              parentId: parentId,
              title: categoryName,
              contexts: ["selection"]
            }, () => {
              if (chrome.runtime.lastError) {
                console.error(`Error creating category menu '${categoryName}':`, chrome.runtime.lastError);
              } else {
                console.log(`Category menu '${categoryName}' created.`);
              }
            });

            // Add endpoints for this category
            category.items.forEach(endpoint => {
              chrome.contextMenus.create({
                id: endpoint.path,
                parentId: categoryId,
                title: `${endpoint.method} ${endpoint.path}`,
                contexts: ["selection"]
              }, () => {
                if (chrome.runtime.lastError) {
                  console.error(`Error creating menu item for ${endpoint.method} ${endpoint.path}:`, chrome.runtime.lastError);
                } else {
                  console.log(`Menu item for ${endpoint.method} ${endpoint.path} created.`);
                }
              });
            });

            // Recursively create subcategories
            if (Object.keys(category.subcategories).length > 0) {
              createMenuItems(category.subcategories, categoryId);
            }
          }
        }

        // Start creating the menu structure from the top level
        createMenuItems(categorized, "parentMenu");
      }

      console.log("Context menu created successfully.");

      // If context menu creation is successful, reset retry parameters
      if (retryTimer) {
        clearTimeout(retryTimer);
        retryTimer = null;
        retryCount = 0;
        currentRetryInterval = INITIAL_RETRY_INTERVAL;
        console.log("Retry mechanism reset after successful context menu creation.");
      }

      // Notify user of successful refresh
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: 'Extension Refreshed',
        message: 'Context menu has been refreshed successfully.',
        priority: 1
      });

      return { success: true };

    } catch (error) {
      console.error("Error creating context menu:", error);

      // Notify user of the error
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: 'Refresh Failed',
        message: `Unable to refresh context menu: ${error.message}`,
        priority: 2
      });

      // Initiate retry with exponential backoff
      if (retryCount < MAX_RETRIES) {
        retryCount++;
        console.log(`Retrying to create context menu (${retryCount}/${MAX_RETRIES}) in ${currentRetryInterval / 1000} seconds...`);
        if (!retryTimer) {
          retryTimer = setTimeout(createContextMenu, currentRetryInterval);
          currentRetryInterval = Math.min(currentRetryInterval * 2, MAX_RETRY_INTERVAL);
        }
      } else {
        console.error("Max retry attempts reached. Unable to create context menu.");
        // Final notification after max retries
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon128.png',
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

  // Handle context menu clicks
  chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    if (info.menuItemId && info.selectionText) {
      const selectedText = info.selectionText;
      const pageUrl = tab.url; // Get the URL of the current tab
      const { serverAddress, apiKey } = await getServerConfig();

      console.log(`Sending selected text to ${serverAddress}${info.menuItemId}`);

      // Send the text and URL to the chosen endpoint with API key
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
        console.log(`Response from ${info.menuItemId}:`, data);

        // Optionally, notify the user of successful send
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon128.png',
          title: 'Send Successful',
          message: `Text sent successfully to ${info.menuItemId}.`,
          priority: 1
        });

      } catch (error) {
        console.error("Error sending text:", error);
        // Notify the user about the error
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon128.png',
          title: 'Send Failed',
          message: `Unable to send text: ${error.message}`,
          priority: 2
        });
      }
    }
  });

  // Listen for messages from popup or other parts of the extension
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "refreshContextMenu") {
      console.log("Received 'refreshContextMenu' message.");
      createContextMenu().then((result) => {
        sendResponse(result);
      }).catch((error) => {
        console.error("Error in 'refreshContextMenu':", error);
        sendResponse({ success: false });
      });
      // Return true to indicate that sendResponse will be called asynchronously
      return true;
    }
  });

  // Listen for keyboard commands
  chrome.commands.onCommand.addListener((command) => {
    console.log(`Command received: ${command}`);
    if (command === "refresh-context-menu") {
      createContextMenu();
    } else if (command === "open-options-page") {
      chrome.runtime.openOptionsPage();
    }
  });

  // Listen for changes in storage to handle updated server address or API key
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "sync" && (changes.serverAddress || changes.apiKey)) {
      console.log("Server address or API key changed. Recreating context menu...");
      createContextMenu();
    }
  });

  // Create the context menu when the extension is installed
  chrome.runtime.onInstalled.addListener(() => {
    console.log("Extension installed. Attempting to create context menu...");
    createContextMenu();
  });

  // Also attempt to create the context menu when the browser starts
  chrome.runtime.onStartup.addListener(() => {
    console.log("Browser started. Attempting to create context menu...");
    createContextMenu();
  });
