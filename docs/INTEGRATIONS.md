# Reflow — Integration Guide (n8n & Webhooks)

This guide demonstrates integrating Reflow Public API v1 into external workflow automation engines (such as n8n) and verifying outbound webhook signatures.

---

## 1. n8n HTTP Request Node Setup

To ingest content or schedule publications from an n8n workflow:

1. Add an **HTTP Request** node in n8n.
2. Set Method to `POST`.
3. Set URL to `http://reflow-host:8000/api/v1/content/text` (or `/publications`).
4. Set Authentication to `Header Auth`:
   - Header Name: `Authorization`
   - Header Value: `Bearer reflow_live_...`
5. Pass `Idempotency-Key` header to prevent duplicate execution during workflow retries:
   - Header Name: `Idempotency-Key`
   - Header Value: `={{ $json.id }}`

---

## 2. Webhook HMAC Signature Verification

Reflow sends outbound HTTPS webhook payloads with a digital signature header:
```http
X-Reflow-Signature: sha256=a1b2c3d4e5f6...
```

### Python HMAC Verification Example

```python
import hmac
import hashlib

def verify_reflow_signature(payload_bytes: bytes, header_signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_signature)
```

### TypeScript / Node.js Verification Example

```typescript
import crypto from 'crypto';

export function verifyReflowSignature(payload: string, headerSignature: string, secret: string): boolean {
  const expected = 'sha256=' + crypto.createHmac('sha256', secret).update(payload).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(headerSignature));
}
```
