# Feature Design: Message Encryption (Transport Layer)

## 1. Problem Statement

Pragna is a personal AI platform. When accessed over a corporate or shared network, the message content (user prompts and LLM responses) travels over HTTPS but is visible in plaintext to any intermediary that performs **TLS/SSL inspection** — a common enterprise proxy technique where the proxy terminates TLS, reads the body, and re-encrypts with a corporate CA certificate.

This feature adds an **application-layer encryption** envelope on top of HTTPS so that message content is encrypted before it leaves the browser and decrypted only after it arrives at the server — and vice versa for responses. The network (and any proxy sitting on it) sees only ciphertext regardless of whether TLS inspection is active.

### What this protects against

| Threat | Protected? |
|---|---|
| Corporate proxy reading message bodies (no SSL inspection) | Yes — HTTPS alone already covers this |
| Corporate proxy with SSL inspection reading message bodies | Yes — app-layer ciphertext survives SSL interception |
| ISP / network tap on HTTPS traffic | Yes |
| Passive packet capture / logging at edge | Yes |

### What this does NOT protect against

| Threat | Protected? |
|---|---|
| Endpoint monitoring on company device (keyloggers, screen capture) | No |
| Pragna server itself reading messages | No — server must decrypt to call LLMs |
| Database breach (messages stored plaintext in DB) | No — out of scope, tracked separately |
| Metadata (which domain you visit, request frequency, payload size) | No — HTTPS hides body, not metadata |

### Prerequisite: SSL Inspection Check

Before relying on this feature, verify that your network is NOT replacing TLS certificates. In Chrome/Edge: padlock → Connection is secure → Certificate is valid → check **Issued by**. If it shows `Let's Encrypt`, `DigiCert`, or a known public CA, your TLS is intact and no SSL inspection is active. If it shows a corporate CA name, see [Limitations](#7-limitations).

---

## 2. Design Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Browser                                                         │
│                                                                 │
│  User types message                                             │
│       ↓                                                         │
│  AES-256-GCM encrypt (key from localStorage)                    │
│       ↓                                                         │
│  { iv: "...", ciphertext: "..." }  ──── HTTPS ────►  Server    │
│                                                                 │
│  ◄─── HTTPS ────  { iv: "...", ciphertext: "..." }              │
│       ↓                                                         │
│  AES-256-GCM decrypt (key from localStorage)                    │
│       ↓                                                         │
│  Render LLM response                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Server                                                          │
│                                                                 │
│  Receive { iv, ciphertext }                                     │
│       ↓                                                         │
│  AES-256-GCM decrypt (user key from DB)                         │
│       ↓                                                         │
│  Plaintext prompt → LangGraph → LLMs                            │
│       ↓                                                         │
│  LLM response plaintext                                         │
│       ↓                                                         │
│  AES-256-GCM encrypt (user key from DB)                         │
│       ↓                                                         │
│  SSE stream { iv, ciphertext } chunks                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Algorithm Choice

**AES-256-GCM** (Galois/Counter Mode)

- Industry standard symmetric authenticated encryption
- Natively supported in browsers via `window.crypto.subtle` — no third-party library needed
- Natively supported in Python via `cryptography` library (already a dependency)
- GCM mode provides both confidentiality and integrity (detects tampering)
- 256-bit key = 32 random bytes
- Each encryption operation requires a fresh 96-bit (12-byte) IV/nonce — never reuse

---

## 4. Key Lifecycle

### 4.1 Key Generation (one-time, at account creation)

- Server generates `os.urandom(32)` → 256-bit AES key
- Stored in the `users` table as a new column `message_enc_key`, encrypted at rest using the existing `SETTINGS_SECRET` Fernet key (same pattern as user LLM API keys)
- Never logged, never returned in API responses except the one delivery event at login

### 4.2 Key Delivery (at login)

- After Auth0 callback and JWT issuance, the existing `/auth/session` or login response includes the key as a base64-encoded field
- Browser stores it in `localStorage` under a fixed key (e.g., `pragna_enc_key`)
- This is the only moment the key crosses the network — protected by HTTPS

### 4.3 Key in Memory (browser runtime)

- On app load, read key from `localStorage`, import via `window.crypto.subtle.importKey()` into a `CryptoKey` object
- The `CryptoKey` is non-extractable after import — the raw bytes are not accessible to JS after the initial import, reducing XSS exposure
- Held in a module-level variable in `useAgentChat.js` or a dedicated `useEncryption.js` composable

### 4.4 Key Rotation

- Not in scope for v1
- Future: add a `key_version` column; rotate on user request; re-encrypt all stored messages during rotation window

---

## 5. Request / Response Flow (Detailed)

### 5.1 Outbound (User Message)

```
Browser:
  plaintext = user input string
  iv = crypto.getRandomValues(new Uint8Array(12))
  ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, cryptoKey, encode(plaintext))
  body = { iv: base64(iv), ciphertext: base64(ciphertext) }
  POST /api/chat/stream  ← sends encrypted body

Server (api/routes/chat.py):
  iv, ciphertext = base64_decode(body.iv), base64_decode(body.ciphertext)
  user_key = fetch_user_enc_key(user_id)  ← from DB, Fernet-decrypted
  plaintext = aes_gcm_decrypt(user_key, iv, ciphertext)
  → pass plaintext into LangGraph as normal
```

### 5.2 Inbound (LLM Response via SSE)

Two options — see [Performance section](#6-performance-and-scalability).

**Option A — Encrypt full response at end (no streaming)**
```
Server:
  Collect full LLM output string
  iv = os.urandom(12)
  ciphertext = aes_gcm_encrypt(user_key, iv, full_response)
  emit single SSE event: { iv, ciphertext }

Browser:
  On SSE done event, decrypt full ciphertext → render
```

**Option B — Encrypt per SSE chunk (preserves streaming)**
```
Server:
  For each token chunk emitted by LangGraph:
    iv = os.urandom(12)  ← fresh IV per chunk
    ciphertext = aes_gcm_encrypt(user_key, iv, chunk)
    emit SSE token event: { iv, ciphertext }

Browser:
  On each SSE token event:
    decrypt chunk → append to displayed message
```

Option B preserves the real-time typing effect. Option A is simpler but shows nothing until the full response is ready. **Recommendation: Option B for UX parity with current behavior.**

---

## 6. Performance and Scalability

### 6.1 Encryption/Decryption Latency

| Operation | Location | Estimated Cost |
|---|---|---|
| Encrypt user message (< 10KB) | Browser (Web Crypto, hardware-accelerated) | < 1ms |
| Decrypt user message | Server (Python `cryptography`) | < 1ms |
| Encrypt LLM response (per chunk, ~5-50 bytes) | Server | < 0.1ms per chunk |
| Decrypt LLM chunk | Browser (Web Crypto) | < 0.1ms per chunk |

Runtime overhead is **negligible**. The bottleneck remains network latency and LLM token generation speed, not encryption.

### 6.2 SSE Streaming Overhead (Option B)

A typical LLM response emits 200–800 token chunks. Each chunk adds:
- 12 bytes IV → 16 bytes base64
- 16 bytes GCM authentication tag per chunk
- ~33% base64 size inflation on ciphertext

Approximate overhead per response: **3–8 KB of extra bytes**. Negligible on any modern connection.

Browser-side: each `token` SSE event triggers one `crypto.subtle.decrypt()` call. Web Crypto is async and non-blocking. No UI jank expected.

### 6.3 Server Memory

Option B (per-chunk): stateless per chunk, no buffering needed.  
Option A (full response): must buffer the entire LLM response in memory before encrypting. For long architecture documents (10,000+ tokens), this could be 40–80KB per active session held in memory. Acceptable at current scale, worth noting for future high-concurrency scenarios.

### 6.4 Database Impact

One new column (`message_enc_key`, ~64 bytes encrypted) on the `users` table. Read once at login, not on every request. Zero query overhead on the hot path.

### 6.5 Horizontal Scaling

The key is fetched from the database at login and delivered to the browser. On subsequent requests, the server re-fetches the key from DB per request (or caches it in the session). Since the key lives in the database, it is available to all backend pods equally — **no shared memory, no sticky sessions required**. Fully compatible with the current K3s multi-replica setup.

### 6.6 Key Delivery at Login — Single Point of Sensitivity

The only moment the raw key (Fernet-decrypted) crosses the network is the login response. This is protected by HTTPS. If this concern grows (e.g., moving to zero-trust architecture), the key can be derived from a combination of server component + user password (split-key design) — but this is out of scope for v1.

---

## 7. Limitations

### 7.1 SSL Inspection (Corporate MITM Proxy)

If the corporate network uses TLS interception (Zscaler, Palo Alto, etc.), the HTTPS connection is terminated at the proxy. The key delivery at login is visible to the proxy. Once the proxy has the key, all subsequent encrypted messages can be decrypted.

**Detection:** If the certificate issuer in your browser shows a corporate CA instead of Let's Encrypt, SSL inspection is active.

**Mitigation (out of scope for v1):** Derive the encryption key from the user's password locally using PBKDF2/Argon2 so the key never travels the network. This requires the server to also derive the key — only possible if the server also knows the password, which conflicts with Auth0 (password-less OAuth). A split-key or hardware-token approach would be required. Complex; deferred.

### 7.2 Endpoint Monitoring

On a company-managed device, IT may run endpoint agents (CrowdStrike, Carbon Black, Jamf) that capture keystrokes or screenshots at the OS level — before the browser encrypts anything. This feature provides no protection against endpoint monitoring.

### 7.3 Metadata Visibility

The domain, IP, request frequency, and approximate payload sizes remain visible regardless of payload encryption. The employer can see that you are using the service, even if not what you are saying.

### 7.4 XSS Attack Surface

The encryption key in `localStorage` is accessible to any JavaScript running on the page, including injected scripts via XSS. Mitigation: strict CSP headers (`Content-Security-Policy`), no inline scripts, and importing the key as non-extractable `CryptoKey` object.

### 7.5 No Forward Secrecy

This is a static symmetric key. If the key is ever compromised, all past and future messages encrypted with it are vulnerable. Forward secrecy (per-session ephemeral keys) is out of scope for v1.

### 7.6 Database Storage (Plaintext)

Messages are stored in the database in plaintext after server-side decryption. This feature protects transit only. At-rest encryption is a separate initiative.

---

## 8. Affected Components

| Component | Change |
|---|---|
| `persistence/checkpointer.py` | Add `message_enc_key` column to `users` table; generate key on user creation |
| `api/routes/auth.py` | Include base64-encoded key in login/session response |
| `api/routes/chat.py` | Decrypt incoming message body; encrypt outgoing SSE token chunks |
| `utils/encryption.py` (new) | AES-256-GCM encrypt/decrypt helpers using `cryptography` library |
| `frontend/src/composables/useEncryption.js` (new) | Web Crypto key import, encrypt, decrypt helpers |
| `frontend/src/composables/useAgentChat.js` | Encrypt before send; decrypt each incoming SSE `token` event |
| `frontend/src/views/SettingsView` | (Optional) Key rotation UI in future |

---

## 9. Open Questions

1. **Key rotation UX:** What happens to existing chat history (stored plaintext) if the key is rotated? No impact today since DB is plaintext, but needs design when at-rest encryption is added.
2. **Multi-device:** If the user logs in on two devices, both get the same key from DB. This is fine for symmetric encryption — both can decrypt each other's messages.
3. **Key loss:** If the DB row is deleted or corrupted, the key is unrecoverable and new messages can't be decrypted by old clients until they re-login. Low risk given DB backups.
4. **Non-chat endpoints:** Settings, session metadata, and other API calls are not encrypted by this feature. Only the chat message body is in scope.
5. **Option A vs B for SSE:** Final call on per-chunk vs full-response encryption for the SSE stream. Recommendation is Option B but needs sign-off before implementation.
