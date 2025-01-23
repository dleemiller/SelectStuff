// encryption.js

// Function to generate a key
async function generateKey() {
  return await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"]
  );
}

// Function to encrypt data
async function encryptData(key, data) {
  const encoder = new TextEncoder();
  const iv = crypto.getRandomValues(new Uint8Array(12)); // Initialization vector
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(data)
  );
  return { iv, encrypted };
}

// Function to decrypt data
async function decryptData(key, iv, data) {
  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    key,
    data
  );
  const decoder = new TextDecoder();
  return decoder.decode(decrypted);
}

export { generateKey, encryptData, decryptData };
