# Reflow — Public REST API Specification

Reflow exposes a comprehensive, RESTful OpenAPI-compliant HTTP interface.

---

## 1. Authentication & API Keys

Public API calls accept Bearer Token authentication using API Keys:
```http
Authorization: Bearer reflow_live_...
```

### Creating API Keys
API keys can be generated via `POST /api/auth/api-keys`. The raw key is returned **ONLY ONCE** upon creation and stored in database using SHA-256 hashing.

| Endpoint | Method | Scope Required | Description |
|---|---|---|---|
| `/api/auth/api-keys` | `POST` | Admin | Generate new API key |
| `/api/auth/api-keys` | `GET` | Admin | List registered API keys |
| `/api/auth/api-keys/{id}` | `DELETE` | Admin | Revoke an API key |

---

## 2. Plugins API

| Endpoint | Method | Description |
|---|---|---|
| `/api/plugins` | `GET` | List all registered plugins and status |
| `/api/plugins/{id}` | `GET` | Get single plugin metadata |
| `/api/plugins/{id}/enable` | `POST` | Enable an installed plugin |
| `/api/plugins/{id}/disable` | `POST` | Disable a plugin |
| `/api/plugins/{id}/health` | `POST` | Execute isolated plugin health check |

---

## 3. Outbound Webhooks API

| Endpoint | Method | Description |
|---|---|---|
| `/api/webhooks` | `GET` | List registered webhook endpoints |
| `/api/webhooks` | `POST` | Create outbound webhook endpoint |
| `/api/webhooks/{id}` | `DELETE` | Delete webhook endpoint |
| `/api/webhooks/{id}/test` | `POST` | Send test signed delivery payload |

### Webhook Signatures
Webhooks include an HMAC-SHA256 signature header:
```http
X-Reflow-Signature: t=1756760000,v1=5d41402abc4b2a76b9719d911017c592
```

---

## 4. Core Content APIs

| Endpoint | Method | Description |
|---|---|---|
| `/api/content` | `GET` | List ingested content assets |
| `/api/content/upload` | `POST` | Upload video, audio, image, PDF |
| `/api/content/{id}` | `GET` | Fetch single content item workspace data |
| `/api/content/{id}/clips` | `GET` | List short-form clips |
| `/api/publications` | `GET` | List publications across platforms |
| `/api/publications/scheduled` | `GET` | List scheduled publications |
| `/api/search?q={query}` | `GET` | Server-side global search |
