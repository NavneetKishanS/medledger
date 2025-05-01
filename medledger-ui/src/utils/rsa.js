// src/utils/rsa.js

/**
 * Encrypts a message using the provided RSA public key in PEM format.
 * Returns a base64-encoded ciphertext string.
 */
export async function encryptWithPublicKey(publicKeyPem, message) {
    const encoder = new TextEncoder();
    const data = encoder.encode(message);
  
    // Import the PEM key
    const key = await window.crypto.subtle.importKey(
      "spki",
      pemToArrayBuffer(publicKeyPem),
      {
        name: "RSA-OAEP",
        hash: "SHA-256",
      },
      false,
      ["encrypt"]
    );
  
    const encrypted = await window.crypto.subtle.encrypt(
      { name: "RSA-OAEP" },
      key,
      data
    );
  
    return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
  }
  
  /**
   * Converts PEM-formatted string to ArrayBuffer
   */
  function pemToArrayBuffer(pem) {
    const b64Lines = pem.replace(/-----(BEGIN|END) PUBLIC KEY-----/g, "").trim();
    const b64 = b64Lines.replace(/\s+/g, "");
    const binaryString = atob(b64);
    const bytes = new Uint8Array([...binaryString].map((char) => char.charCodeAt(0)));
    return bytes.buffer;
  }
  