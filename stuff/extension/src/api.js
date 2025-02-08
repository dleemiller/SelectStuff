// api.js
import { delay } from './utils.js';

const DESIRED_TAGS = ["Select/"];

export async function getServerConfig() {
  try {
    const data = await chrome.storage.sync.get(["serverAddress", "apiKey"]);
    return {
      serverAddress: data.serverAddress || "http://localhost:8000",
      apiKey: data.apiKey || ""
    };
  } catch (error) {
    console.error("Failed to retrieve server configuration:", error);
    return {
      serverAddress: "http://127.0.0.1:8000",
      apiKey: ""
    };
  }
}

export async function fetchEndpoints() {
  const { serverAddress, apiKey } = await getServerConfig();
  console.log('Attempting to fetch endpoints with config:', {
    serverAddress,
    hasApiKey: !!apiKey
  });

  try {
    // Check root endpoint
    const rootCheck = await fetch(`${serverAddress}/`);
    console.log('Root endpoint check:', {
      ok: rootCheck.ok,
      status: rootCheck.status
    });

    // Health check
    const healthCheck = await fetch(`${serverAddress}/health`, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      headers: { 'Accept': 'application/json' }
    });
    console.log('Health check response:', {
      ok: healthCheck.ok,
      status: healthCheck.status
    });

    // Fetch the OpenAPI schema (note: removed accidental whitespace)
    const response = await fetch(`${serverAddress}/openapi.json`, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      headers: { 'Accept': 'application/json' }
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

    const postEndpoints = [];
    for (const path in data.paths) {
      const methods = data.paths[path];
      for (const method in methods) {
        if (method.toLowerCase() === "post") {
          const endpointInfo = methods[method];
          const endpoint = {
            path,
            method: method.toUpperCase(),
            tags: endpointInfo.tags || []
          };

          const hasDesiredTag = endpoint.tags.some(tag =>
            DESIRED_TAGS.some(desiredTag => tag.startsWith(desiredTag))
          );
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

